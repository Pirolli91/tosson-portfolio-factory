# Portfolio Factory + Auction Intelligence v2

Built by Temitope D. Soneye (Tosson Services LLC dba Tosson Environmental Analytics) — Sprint 5, 2026-11-23. Every artifact in this repo actually runs: the numbers reconcile, the DAG executes, and every claim in the hiring-manager README is traceable to a runnable artifact in `proof-registry.json`.

## Build A — Job-Hunt Portfolio Factory (`portfolio-factory/`)
A working dbt + DuckDB + Airflow data pipeline on public EPA UCMR 5 PFAS occurrence data:
- **Ingest** — EPA UCMR 5 NC extract reconciled exactly (68,633 source rows == 68,633 loaded), 291/291 NC water systems county-mapped via EPA SDWIS.
- **dbt warehouse** — staging → intermediate → marts (county scorecard, analyte summary, system screening vs the 2024 EPA MCL benchmarks — screening comparison only, never a compliance claim). `dbt build` 59/59 PASS; docs generated under `pfas_warehouse/target/`.
- **Airflow 3.4.0 DAG** — ingest → dbt run → dbt test → run summary; clean run + scheduler backfill evidenced in `portfolio-factory/reports/`; a failing dbt test halts the pipeline before anything publishes.
- **SQL + BI proof pack** — 10 advanced SQL patterns executed against the marts; Snowflake-dialect translations (labelled dialect-only, not executed); Power BI DAX measure library + semantic-model spec (no .pbix).
- **Interactive dashboard** — `portfolio-factory/dashboard/index.html`, a self-contained county screening explorer built from the marts.
- **Claim verifier + JD gap analyser** — `verifier/verify_packet.py` scores application-packet claims against the proof registry + base documents (PROVEN_BY_ARTIFACT / IN_BASE_DOCS / UNSUPPORTED / FORBIDDEN); `gap_analyser/` ranks JD gaps from live-captured postings.

## Build B — Auction Intelligence v2 (`auction-intel-v2/`)
Read-only analytics (no bidding, no account actions): manifest ROI analyser with shown arithmetic and STRONG/MARGINAL/PASS bands, HiBid re-list churn tracker (title similarity + perceptual image hash), fail-closed NC land parcel scorer, and a strictly isolated Kia Carnival monitor (VIN decode, SC266 recall check, trim filter, finance-clause checklist generator).

## Verification
`pytest` — 35 tests, passing with no fixtures folder present (synthetic mini-fixtures under `tests/`). Note: 4 small synthetic PNG fixtures used by the HiBid image-hash test and 2 dbt build-cache files are binary and live in the canonical deliverable archive rather than this snapshot; all other content is identical.

## Rules this repo was built under
Public data only (EPA UCMR 5 / SDWIS / NHTSA — public domain). UCMR 5 results are occurrence/screening comparisons against MCL benchmarks, never violation or compliance claims. Nothing here submits, bids, buys, or sends.
