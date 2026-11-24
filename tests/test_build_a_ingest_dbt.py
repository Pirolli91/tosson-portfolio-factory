"""Build A1 + A2 self-verifying tests (passes with NO fixtures/ directory).

Tests repeatable EPA UCMR 5 ingest, SDWIS county enrichment + UNMAPPED_COUNTY
fallback, exact row reconciliation, and full dbt seed + run + test execution
on synthetic mini-fixtures under tests/fixtures_synthetic/build_a/.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WORKSPACE_ROOT / "portfolio-factory"
SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_a"
DBT_DIR = REPO_ROOT / "pfas_warehouse"


def _resolve_dbt_bin() -> str:
    candidates = [
        os.environ.get("PFAS_DBT_BIN"),
        str(WORKSPACE_ROOT / ".venv" / "bin" / "dbt"),
        str(Path(sys.executable).parent / "dbt"),
        shutil.which("dbt"),
    ]
    for cand in candidates:
        if cand and Path(cand).exists():
            return str(cand)
    return "dbt"


DBT_BIN = _resolve_dbt_bin()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ingest.ingest_ucmr5 import run_ingest


def test_ingest_and_dbt_build_on_synthetic_mini_fixture(tmp_path: Path) -> None:
    db_path = tmp_path / "synthetic_ucmr5.duckdb"
    summary = run_ingest(
        input_file=SYNTH_DIR / "ucmr5_mini.tsv",
        county_file=SYNTH_DIR / "sdwis_counties_mini.csv",
        db_path=db_path,
        logical_date="2026-11-01",
        skip_registry=True,
    )

    # 20 NC rows in ucmr5_mini.tsv; 2 VA rows must be filtered out
    assert summary["source_nc_rows"] == 20
    assert summary["loaded_nc_rows"] == 20
    assert summary["reconciled"] is True
    assert summary["distinct_pwsids"] == 3
    assert summary["mapped_pwsids"] == 2
    assert summary["unmapped_pwsids"] == 1
    assert len(summary["source_file_sha256"]) == 64

    # Execute dbt build (seed + 8 models + 50 schema/singular tests) on synthetic DB
    env = os.environ.copy()
    env["PFAS_DUCKDB_PATH"] = str(db_path)
    proc = subprocess.run(
        [
            DBT_BIN,
            "build",
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
            "--target-path",
            str(tmp_path / "dbt_target"),
            "--log-path",
            str(tmp_path / "dbt_logs"),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"dbt build failed:\n{proc.stdout}\n{proc.stderr}"

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        # Unmapped PWSID NC0100003 must be preserved as UNMAPPED_COUNTY, never dropped
        counties = {
            r[0]: r[1]
            for r in con.execute(
                "SELECT county_name, systems_monitored FROM main_marts.mart_county_scorecard"
            ).fetchall()
        }
        assert counties == {"Wake": 1, "Cumberland": 1, "UNMAPPED_COUNTY": 1}

        # Verify Hazard Index mixture calculation on NC0100002 (2024-03-20):
        # PFHxS 6/10 (0.6) + PFNA 5/10 (0.5) + PFBS 200/2000 (0.1) = 1.2 > 1.0
        hi_row = con.execute(
            """
            SELECT hazard_index_score, above_hi_benchmark_flag
            FROM main_intermediate.int_system_hazard_index
            WHERE pwsid = 'NC0100002' AND collection_date = DATE '2024-03-20'
            """
        ).fetchone()
        assert hi_row is not None
        assert abs(float(hi_row[0]) - 1.2) < 1e-4
        assert hi_row[1] is True

        # Verify system mart reconciles all 20 rows across 3 systems
        sys_sum = con.execute(
            "SELECT COUNT(*), SUM(total_samples) FROM main_marts.mart_system_screening"
        ).fetchone()
        assert sys_sum == (3, 20)
    finally:
        con.close()


def test_committed_dbt_docs_artifacts_exist_and_screening_only_language() -> None:
    target_dir = DBT_DIR / "target"
    for fname in ("manifest.json", "catalog.json", "index.html", "run_results.json"):
        p = target_dir / fname
        assert p.exists() and p.stat().st_size > 100, f"Missing dbt docs artifact: {p}"

    banned = "violat" + "ion"
    for path in list((DBT_DIR / "models").rglob("*")) + list((DBT_DIR / "tests").rglob("*")):
        if path.is_file():
            content = path.read_text(encoding="utf-8").lower()
            assert banned not in content, f"Forbidden screening term found in {path}"
