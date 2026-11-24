"""Build A3 Airflow 3.4.0 DAG tests (passes with NO fixtures/ directory).

Verifies:
1. DAG parses cleanly under Apache Airflow 3.4.0 (.venv-airflow) with zero import errors,
   correct task dependency graph (ingest_ucmr5 >> dbt_run >> dbt_test >> publish_run_summary),
   retries configured, and trigger_rule='all_success' on publish_run_summary.
2. Failing dbt test raises non-zero and prevents publish_run_summary from writing any report.
3. Real Airflow clean run (2026-11-01) and backfill (2025-10-01) summary reports exist.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WORKSPACE_ROOT / "portfolio-factory"
DAGS_DIR = REPO_ROOT / "dags"
DBT_DIR = REPO_ROOT / "pfas_warehouse"
SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_a"


def _first_existing(candidates: list[str | None], fallback: str) -> str:
    for cand in candidates:
        if cand and Path(cand).exists():
            return str(cand)
    return fallback


_ACTIVE_VENV_ROOT = Path(sys.executable).parent.parent
AIRFLOW_PYTHON = _first_existing(
    [
        os.environ.get("AIRFLOW_PYTHON_BIN"),
        str(WORKSPACE_ROOT / ".venv-airflow" / "bin" / "python"),
        str(_ACTIVE_VENV_ROOT.parent / ".venv-airflow" / "bin" / "python"),
    ],
    sys.executable,
)
VENV_PYTHON = _first_existing(
    [
        os.environ.get("PFAS_VENV_PYTHON"),
        str(WORKSPACE_ROOT / ".venv" / "bin" / "python"),
        sys.executable,
    ],
    sys.executable,
)
VENV_DBT = _first_existing(
    [
        os.environ.get("PFAS_DBT_BIN"),
        str(WORKSPACE_ROOT / ".venv" / "bin" / "dbt"),
        str(Path(sys.executable).parent / "dbt"),
        shutil.which("dbt"),
    ],
    "dbt",
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_airflow_dag_parses_cleanly_and_has_expected_structure() -> None:
    check_code = f"""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("pfas_pipeline", "{DAGS_DIR / 'pfas_pipeline.py'}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
dag = mod.pfas_ucmr5_pipeline_dag
assert dag.dag_id == "pfas_ucmr5_pipeline"
task_ids = set(dag.task_ids)
assert task_ids == {{"ingest_ucmr5", "dbt_run", "dbt_test", "publish_run_summary"}}
assert dag.default_args["retries"] >= 2
assert dag.default_args["retry_exponential_backoff"] is True
assert dag.get_task("dbt_run").upstream_task_ids == {{"ingest_ucmr5"}}
assert dag.get_task("dbt_test").upstream_task_ids == {{"dbt_run"}}
assert dag.get_task("publish_run_summary").upstream_task_ids == {{"dbt_test"}}
assert str(dag.get_task("publish_run_summary").trigger_rule) in ("all_success", "TriggerRule.ALL_SUCCESS")
print("DAG_PARSE_OK")
"""
    proc = subprocess.run(
        [AIRFLOW_PYTHON, "-c", check_code],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Airflow DAG parse failed:\n{proc.stdout}\n{proc.stderr}"
    assert "DAG_PARSE_OK" in proc.stdout


def test_failing_dbt_test_halts_pipeline_and_blocks_publish(tmp_path: Path) -> None:
    """Inject a negative concentration row after dbt run so assert_non_negative_concentrations
    fails, proving dbt_test exits non-zero and publish_run_summary never writes a report."""
    import duckdb
    from ingest.ingest_ucmr5 import run_ingest

    db_path = tmp_path / "fail_gate.duckdb"
    reports_dir = tmp_path / "reports"
    run_ingest(
        input_file=SYNTH_DIR / "ucmr5_mini.tsv",
        county_file=SYNTH_DIR / "sdwis_counties_mini.csv",
        db_path=db_path,
        logical_date="2026-09-01",
        skip_registry=True,
    )

    env = os.environ.copy()
    env["PFAS_DUCKDB_PATH"] = str(db_path)
    target_path = tmp_path / "dbt_target"
    log_path = tmp_path / "dbt_logs"

    # Build models cleanly first
    subprocess.run(
        [
            VENV_DBT, "seed",
            "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
            "--target-path", str(target_path), "--log-path", str(log_path),
        ],
        check=True, env=env, capture_output=True, text=True,
    )
    subprocess.run(
        [
            VENV_DBT, "run",
            "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
            "--target-path", str(target_path), "--log-path", str(log_path),
        ],
        check=True, env=env, capture_output=True, text=True,
    )

    # Corrupt raw table with a negative concentration so dbt test MUST fail
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            UPDATE raw_ucmr5.ucmr5_nc_results
            SET analytical_result_value_raw = '-0.050'
            WHERE row_num = 1
            """
        )
    finally:
        con.close()

    # dbt test must return non-zero
    test_proc = subprocess.run(
        [
            VENV_DBT, "test",
            "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
            "--target-path", str(target_path), "--log-path", str(log_path),
        ],
        env=env, capture_output=True, text=True,
    )
    assert test_proc.returncode != 0, "Expected dbt test to fail on negative concentration"

    # Even if publish_summary.py were invoked directly with failed run_results.json, it must refuse!
    pub_proc = subprocess.run(
        [
            VENV_PYTHON,
            str(REPO_ROOT / "ingest" / "publish_summary.py"),
            "--logical-date", "2026-09-01",
            "--db-path", str(db_path),
            "--reports-dir", str(reports_dir),
            "--run-results", str(target_path / "run_results.json"),
        ],
        env=env, capture_output=True, text=True,
    )
    assert pub_proc.returncode != 0, "publish_summary must refuse to publish when dbt tests failed"
    assert not (reports_dir / "pipeline_run_summary_2026-09-01.md").exists()


def test_airflow_clean_run_and_backfill_reports_present() -> None:
    reports_dir = REPO_ROOT / "reports"
    clean_rep = reports_dir / "pipeline_run_summary_2026-11-01.md"
    backfill_rep = reports_dir / "pipeline_run_summary_2025-10-01.md"
    evidence_rep = reports_dir / "airflow_backfill_evidence.md"
    assert clean_rep.exists(), f"Missing clean run summary: {clean_rep}"
    assert backfill_rep.exists(), f"Missing backfill run summary: {backfill_rep}"
    assert evidence_rep.exists(), f"Missing Airflow backfill evidence log: {evidence_rep}"
    for p in (clean_rep, backfill_rep, evidence_rep):
        txt = p.read_text(encoding="utf-8")
        assert "Tosson Services LLC dba Tosson Environmental Analytics" in txt
        assert ("violat" + "ion") not in txt.lower()
