"""Build A3: Apache Airflow 3.4.0 TaskFlow DAG (`pfas_ucmr5_pipeline`).

Orchestrates the North Carolina EPA UCMR 5 PFAS screening pipeline:
  ingest_ucmr5 >> dbt_run >> dbt_test >> publish_run_summary

Key guarantees:
- Real Apache Airflow 3.4.0 TaskFlow API (`from airflow.sdk import dag, task`)
  running under LocalExecutor + SQLite WAL (no Docker or external DB required).
- Retries with exponential backoff configured in default_args.
- Subprocess isolation into `.venv` (`PORTFOLIO_VENV_PYTHON`, `PORTFOLIO_VENV_DBT`)
  with `check=True` so any non-zero exit fails the task immediately.
- `publish_run_summary` uses `trigger_rule="all_success"` so a failing `dbt_test`
  halts the DAG with NO silent report publish.
- Screening-only framing enforced throughout; 100% public EPA data.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from airflow.sdk import dag, task

DAGS_DIR = Path(__file__).resolve().parent
REPO_ROOT = DAGS_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent

DEFAULT_VENV_PYTHON = str(WORKSPACE_ROOT / ".venv" / "bin" / "python")
DEFAULT_VENV_DBT = str(WORKSPACE_ROOT / ".venv" / "bin" / "dbt")
DEFAULT_DB_PATH = str(REPO_ROOT / "warehouse" / "pfas_ucmr5.duckdb")
DEFAULT_DBT_DIR = str(REPO_ROOT / "pfas_warehouse")
DEFAULT_REPORTS_DIR = str(REPO_ROOT / "reports")


def _cfg() -> dict[str, str]:
    return {
        "python_bin": os.environ.get("PORTFOLIO_VENV_PYTHON") or DEFAULT_VENV_PYTHON,
        "dbt_bin": os.environ.get("PORTFOLIO_VENV_DBT") or DEFAULT_VENV_DBT,
        "db_path": os.environ.get("PFAS_DUCKDB_PATH") or DEFAULT_DB_PATH,
        "dbt_dir": os.environ.get("PFAS_DBT_PROJECT_DIR") or DEFAULT_DBT_DIR,
        "reports_dir": os.environ.get("PFAS_REPORTS_DIR") or DEFAULT_REPORTS_DIR,
        "input_file": os.environ.get("PFAS_INPUT_FILE", ""),
        "county_file": os.environ.get("PFAS_COUNTY_FILE", ""),
    }


def _subprocess_env(db_path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PFAS_DUCKDB_PATH"] = db_path
    return env


DEFAULT_ARGS = {
    "owner": "tosson_environmental_analytics",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
    "execution_timeout": timedelta(minutes=15),
}


@dag(
    dag_id="pfas_ucmr5_pipeline",
    description="NC EPA UCMR 5 PFAS occurrence screening pipeline: ingest -> dbt run -> dbt test -> publish summary",
    schedule="@monthly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["portfolio", "pfas", "ucmr5", "dbt", "duckdb", "screening-only"],
)
def pfas_ucmr5_pipeline() -> None:
    @task(task_id="ingest_ucmr5")
    def ingest_ucmr5(logical_date: Any = None, ds: str | None = None) -> dict[str, Any]:
        cfg = _cfg()
        run_ds = ds or (
            logical_date.strftime("%Y-%m-%d")
            if hasattr(logical_date, "strftime")
            else datetime.utcnow().strftime("%Y-%m-%d")
        )
        cmd = [
            cfg["python_bin"],
            str(REPO_ROOT / "ingest" / "ingest_ucmr5.py"),
            "--db-path",
            cfg["db_path"],
            "--logical-date",
            run_ds,
            "--skip-registry",
        ]
        if cfg["input_file"]:
            cmd.extend(["--input-file", cfg["input_file"]])
        if cfg["county_file"]:
            cmd.extend(["--county-file", cfg["county_file"]])

        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=_subprocess_env(cfg["db_path"]),
        )
        summary = json.loads(proc.stdout)
        return {
            "logical_date": run_ds,
            "source_nc_rows": summary["source_nc_rows"],
            "loaded_nc_rows": summary["loaded_nc_rows"],
            "reconciled": summary["reconciled"],
            "distinct_pwsids": summary["distinct_pwsids"],
        }

    @task(task_id="dbt_run")
    def dbt_run(ingest_meta: dict[str, Any]) -> dict[str, Any]:
        cfg = _cfg()
        env = _subprocess_env(cfg["db_path"])
        seed_cmd = [
            cfg["dbt_bin"],
            "seed",
            "--project-dir",
            cfg["dbt_dir"],
            "--profiles-dir",
            cfg["dbt_dir"],
        ]
        subprocess.run(seed_cmd, check=True, env=env)

        run_cmd = [
            cfg["dbt_bin"],
            "run",
            "--project-dir",
            cfg["dbt_dir"],
            "--profiles-dir",
            cfg["dbt_dir"],
        ]
        subprocess.run(run_cmd, check=True, env=env)
        return {
            "logical_date": ingest_meta["logical_date"],
            "dbt_run_status": "PASS",
        }

    @task(task_id="dbt_test")
    def dbt_test(run_meta: dict[str, Any]) -> dict[str, Any]:
        cfg = _cfg()
        env = _subprocess_env(cfg["db_path"])
        test_cmd = [
            cfg["dbt_bin"],
            "test",
            "--project-dir",
            cfg["dbt_dir"],
            "--profiles-dir",
            cfg["dbt_dir"],
        ]
        # check=True guarantees any dbt test failure raises CalledProcessError,
        # marking this task FAILED and preventing publish_run_summary from running.
        subprocess.run(test_cmd, check=True, env=env)
        return {
            "logical_date": run_meta["logical_date"],
            "dbt_test_status": "PASS",
        }

    @task(task_id="publish_run_summary", trigger_rule="all_success")
    def publish_run_summary(
        test_meta: dict[str, Any],
        dag_run: Any = None,
    ) -> str:
        cfg = _cfg()
        run_ds = test_meta["logical_date"]
        run_type = str(getattr(dag_run, "run_type", "manual_or_test")) if dag_run else "manual_or_test"
        cmd = [
            cfg["python_bin"],
            str(REPO_ROOT / "ingest" / "publish_summary.py"),
            "--logical-date",
            run_ds,
            "--db-path",
            cfg["db_path"],
            "--reports-dir",
            cfg["reports_dir"],
            "--run-results",
            str(Path(cfg["dbt_dir"]) / "target" / "run_results.json"),
            "--run-type",
            run_type,
        ]
        subprocess.run(cmd, check=True, env=_subprocess_env(cfg["db_path"]))
        return str(Path(cfg["reports_dir"]) / f"pipeline_run_summary_{run_ds}.md")

    ingest_out = ingest_ucmr5()
    run_out = dbt_run(ingest_out)
    test_out = dbt_test(run_out)
    publish_run_summary(test_out)


pfas_ucmr5_pipeline_dag = pfas_ucmr5_pipeline()
