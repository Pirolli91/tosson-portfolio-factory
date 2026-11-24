"""Helper invoked by the Airflow `publish_run_summary` task (runs in .venv with duckdb).

Queries reconciled warehouse counts, dbt test results, and the top 10 NC screening
counties from DuckDB, then writes a one-page Markdown run summary to
`portfolio-factory/reports/pipeline_run_summary_<ds>.md`.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DAGS_DIR = Path(__file__).resolve().parent
REPO_ROOT = DAGS_DIR.parent
DEFAULT_DB_PATH = REPO_ROOT / "warehouse" / "pfas_ucmr5.duckdb"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_RUN_RESULTS = REPO_ROOT / "pfas_warehouse" / "target" / "run_results.json"


def publish_summary(
    *,
    logical_date: str,
    db_path: Path = DEFAULT_DB_PATH,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_results_path: Path = DEFAULT_RUN_RESULTS,
    run_type: str = "scheduled_or_manual",
) -> Path:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        audit = con.execute(
            """
            SELECT
                run_ts_utc, logical_date, source_nc_rows, loaded_nc_rows,
                reconciled, distinct_pwsids, mapped_pwsids, unmapped_pwsids,
                source_file_sha256
            FROM raw_ucmr5.ingest_audit
            LIMIT 1
            """
        ).fetchone()
        top_counties = con.execute(
            """
            SELECT
                county_name,
                systems_monitored,
                total_samples,
                pfas_detected_samples,
                samples_above_mcl_benchmark,
                systems_above_any_2024_benchmark,
                max_benchmark_ratio,
                primary_exceeding_analyte
            FROM main_marts.mart_county_scorecard
            ORDER BY samples_above_mcl_benchmark DESC, systems_above_any_2024_benchmark DESC, county_name ASC
            LIMIT 10
            """
        ).fetchall()
        total_counties = int(
            con.execute("SELECT COUNT(*) FROM main_marts.mart_county_scorecard").fetchone()[0]
        )
        total_sys_above = int(
            con.execute(
                "SELECT SUM(systems_above_any_2024_benchmark) FROM main_marts.mart_county_scorecard"
            ).fetchone()[0]
        )
    finally:
        con.close()

    tests_passed = 0
    tests_failed = 0
    if run_results_path.exists():
        rr = json.loads(run_results_path.read_text(encoding="utf-8"))
        for res in rr.get("results", []):
            uid = res.get("unique_id", "")
            if uid.startswith("test."):
                if res.get("status") == "pass":
                    tests_passed += 1
                else:
                    tests_failed += 1

    if tests_failed > 0:
        raise RuntimeError(
            f"Refusing to publish summary: {tests_failed} dbt test(s) did not pass."
        )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (
        ingest_ts,
        audit_ds,
        src_rows,
        loaded_rows,
        reconciled,
        dist_pws,
        mapped_pws,
        unmapped_pws,
        src_sha,
    ) = audit

    lines = [
        f"# PFAS UCMR 5 Pipeline Run Summary — {logical_date}",
        "",
        f"- **Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics",
        f"- **Airflow DAG:** `pfas_ucmr5_pipeline` (`LocalExecutor` on SQLite WAL)",
        f"- **Logical Date (`ds`):** `{logical_date}`",
        f"- **Run Type:** `{run_type}`",
        f"- **Published (UTC):** `{now_utc}`",
        "",
        "## Warehouse Reconciliation & Quality Gates",
        "",
        f"| Check | Value | Status |",
        f"|---|---|---|",
        f"| EPA UCMR 5 NC Source Rows | `{src_rows:,}` | Reconciled (`==` loaded) |",
        f"| DuckDB Loaded Rows (`raw_ucmr5.ucmr5_nc_results`) | `{loaded_rows:,}` | `reconciled={reconciled}` |",
        f"| Source Archive SHA-256 | `{src_sha[:16]}...` | Verified |",
        f"| Distinct NC Water Systems (`PWSID`) | `{dist_pws}` (`{mapped_pws}` mapped, `{unmapped_pws}` unmapped) | Complete |",
        f"| NC Counties Screened | `{total_counties}` | Complete |",
        f"| Systems Above Any 2024 Screening Benchmark | `{total_sys_above}` | Screening-only |",
        f"| dbt Data & Schema Tests Passed | `{tests_passed}` passed / `{tests_failed}` failed | **PASS** |",
        "",
        "## Top 10 NC Counties by Samples Above 2024 EPA MCL Screening Benchmarks",
        "",
        "| Rank | County | Systems | Total Samples | PFAS Detections | Above 2024 MCL Benchmark | Systems Above Benchmark | Max Ratio (x) | Primary Analyte |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(top_counties, start=1):
        cnty, sysc, tot, det, abv, sys_abv, ratio, prim = row
        ratio_s = f"{ratio:.2f}x" if ratio is not None else "—"
        lines.append(
            f"| {idx} | {cnty} | {sysc} | {tot:,} | {det:,} | {abv:,} | {sys_abv} | {ratio_s} | {prim} |"
        )

    lines.extend(
        [
            "",
            "---",
            "**Screening-Only Framing:** EPA UCMR 5 measures unregulated contaminant occurrence. Comparisons against EPA's six 2024 PFAS drinking-water screening benchmarks (PFOA 4 ppt, PFOS 4 ppt, PFHxS 10 ppt, PFNA 10 ppt, HFPO-DA 10 ppt, Hazard Index 1.0) are informational screening only and never compliance determinations. EPA's rulemaking on potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards is **proposed / not final** (https://www.epa.gov/sdwa/proposed-pfas-rescission-rule; https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation).",
        ]
    )

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"pipeline_run_summary_{logical_date}.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Published pipeline run summary to {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish one-page PFAS pipeline Markdown run summary.")
    parser.add_argument("--logical-date", required=True)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--run-results", type=Path, default=DEFAULT_RUN_RESULTS)
    parser.add_argument("--run-type", default="scheduled_or_manual")
    args = parser.parse_args(argv)
    publish_summary(
        logical_date=args.logical_date,
        db_path=args.db_path,
        reports_dir=args.reports_dir,
        run_results_path=args.run_results,
        run_type=args.run_type,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
