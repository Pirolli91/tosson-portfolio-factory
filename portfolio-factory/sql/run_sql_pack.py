"""Build A4a: Verification runner for the 10 advanced SQL patterns against DuckDB.

Executes queries 01..10 against the dbt-built DuckDB warehouse. Query 04
(incremental MERGE upsert) runs on a temporary scratch copy of the DuckDB
database so the production marts remain untouched and read-only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

SQL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SQL_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from shared.proof_registry import DEFAULT_REGISTRY_PATH, upsert_entry

DEFAULT_DB_PATH = REPO_ROOT / "warehouse" / "pfas_ucmr5.duckdb"
WRITE_QUERIES = {"04_incremental_merge_upsert.sql"}


def _split_sql_statements(sql_text: str) -> list[str]:
    stmts: list[str] = []
    buf: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmts.append("\n".join(buf))
            buf = []
    if buf:
        stmts.append("\n".join(buf))
    return stmts


def run_sql_pack(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    sql_dir: Path = SQL_DIR,
    registry_path: Path | None = DEFAULT_REGISTRY_PATH,
    workspace_root: Path = WORKSPACE_ROOT,
    skip_registry: bool = False,
) -> dict[str, Any]:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB warehouse not found: {db_path}")

    sql_files = sorted(sql_dir.glob("[0-9][0-9]_*.sql"))
    if len(sql_files) != 10:
        raise RuntimeError(f"Expected 10 numbered SQL files in {sql_dir}, found {len(sql_files)}")

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="sql_pack_scratch_") as tmpdir:
        scratch_db = Path(tmpdir) / "scratch.duckdb"
        shutil.copy2(db_path, scratch_db)

        ro_con = duckdb.connect(str(db_path), read_only=True)
        rw_con = duckdb.connect(str(scratch_db))
        try:
            for sql_file in sql_files:
                sql_text = sql_file.read_text(encoding="utf-8")
                is_write = sql_file.name in WRITE_QUERIES
                con = rw_con if is_write else ro_con
                stmts = _split_sql_statements(sql_text)
                last_rows = []
                last_cols: list[str] = []
                for stmt in stmts:
                    rel = con.execute(stmt)
                    if rel.description is not None:
                        last_cols = [d[0] for d in rel.description]
                        last_rows = rel.fetchall()
                if not last_rows:
                    raise RuntimeError(f"Query {sql_file.name} returned 0 rows")
                results.append(
                    {
                        "file": sql_file.name,
                        "mode": "scratch_copy_rw" if is_write else "read_only",
                        "columns": last_cols,
                        "row_count": len(last_rows),
                        "sample_first_row": [str(v) for v in last_rows[0][:6]],
                    }
                )
        finally:
            ro_con.close()
            rw_con.close()

    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "run_ts_utc": run_ts,
        "db_path": str(db_path),
        "queries_executed": len(results),
        "all_passed": True,
        "results": results,
    }

    if not skip_registry and registry_path is not None:
        upsert_entry(
            {
                "artifact_id": "a4a-advanced-sql-pack",
                "kind": "sql_pack",
                "title": "10 Advanced Analytical SQL Patterns Verified Against DuckDB UCMR 5 Marts",
                "repo_path": "portfolio-factory/sql/run_sql_pack.py",
                "evidence": {
                    "command": ".venv/bin/python portfolio-factory/sql/run_sql_pack.py",
                    "result": f"PASS (10/10 SQL patterns executed and verified non-empty against DuckDB marts)",
                    "timestamp": run_ts,
                    "metrics": {
                        "queries_executed": len(results),
                        "query_row_counts": {r["file"]: r["row_count"] for r in results},
                    },
                },
                "supports_claims": [
                    "Authored and executed 10 advanced SQL patterns (window functions, gaps-and-islands, rolling frames, incremental MERGE upsert, IQR/z-score outliers, YoY deltas, Pareto cumulative share, reconciliation) on DuckDB",
                    "SQL",
                    "DuckDB",
                    "Data Quality & Validation",
                ],
                "source_urls": [
                    "https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule",
                    "https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation",
                ],
            },
            registry_path=registry_path,
            workspace_root=workspace_root,
            check_path=True,
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute and verify all 10 advanced SQL patterns.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--skip-registry", action="store_true")
    args = parser.parse_args(argv)

    payload = run_sql_pack(
        db_path=args.db_path,
        registry_path=args.registry_path,
        skip_registry=args.skip_registry,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
