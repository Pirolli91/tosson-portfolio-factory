---
name: build-a-portfolio-factory
description: Operational runbook for Sprint 5 Build A (Job-Hunt Portfolio Factory) covering EPA UCMR 5 NC ingest, dbt-core + DuckDB warehouse, Apache Airflow 3.4.0 LocalExecutor pipeline & backfill, SQL/Snowflake/Power BI/HTML proof pack, Packet Claim-Verifier, and JD Gap Analyser.
---

# Runbook: Build A — Job-Hunt Portfolio Factory

**Owner / Legal Entity:** Temitope Soneye — *Tosson Services LLC dba Tosson Environmental Analytics*  
**Workspace Root:** `/home/antigravity`  
**Repo Root:** `/home/antigravity/portfolio-factory`

## 1. Environments (Venv-Isolated; Zero System-Wide Installs)

- **Core + dbt venv:** `.venv/` (`Python 3.12`, `dbt-core==1.12.7`, `dbt-duckdb==1.11.1`, `duckdb==1.5.6`, `python-docx==1.2.0`, `requests==2.34.2`, `beautifulsoup4==4.15.0`, `PyYAML==6.0.4`, `jsonschema==4.26.0`, `pytest==9.2.0`)
- **Airflow venv:** `.venv-airflow/` (`apache-airflow==3.4.0`, `apache-airflow-core==3.4.0`, `apache-airflow-task-sdk==1.4.0` installed with `constraints-no-providers-3.12.txt`)
- **Environment Variable Names Only** (see `portfolio-factory/.env.example`; never commit values):
  `PFAS_DUCKDB_PATH`, `PROOF_REGISTRY_PATH`, `PORTFOLIO_VENV_PYTHON`, `PORTFOLIO_VENV_DBT`, `AIRFLOW_HOME`, `AIRFLOW__CORE__EXECUTOR`, `AIRFLOW__CORE__DAGS_FOLDER`, `AIRFLOW__CORE__LOAD_EXAMPLES`.

## 2. Standing Guardrails (Check Before Every Run)

1. **Public EPA data only:** Zero proprietary employer data, systems, screenshots, or algorithms anywhere in `portfolio-factory/`.
2. **UCMR 5 screening-only framing:** Occurrence vs 2024 EPA MCL & Hazard Index screening benchmarks only — never frame UCMR 5 results as compliance determinations.
3. **Precise claim language:** Snowflake SQL is strictly **dialect-only (not executed against a Snowflake account)**. Power BI proof rests on `powerbi/measures.dax` + `semantic_model.md` + `model_spec.json` (no `.pbix`).
4. **Read-only:** Nothing submits applications, creates accounts, or bypasses anti-bot/CAPTCHA gates.
5. **Fixtures isolation:** Owner-staged `fixtures/` is strictly read-only and never zipped; all `pytest` suites pass without `fixtures/`.

## 3. End-to-End Execution Steps

### Step A1 — Live EPA UCMR 5 NC Ingest & SDWIS County Enrichment
```bash
.venv/bin/python portfolio-factory/ingest/ingest_ucmr5.py
```
- Downloads/caches EPA UCMR 5 ZIP + EPA SDWIS NC CWS/NTNCWS CSVs under `portfolio-factory/warehouse/raw/`.
- Writes `raw_ucmr5.ucmr5_nc_results`, `raw_ucmr5.sdwis_nc_counties`, and `raw_ucmr5.ingest_audit` in `portfolio-factory/warehouse/pfas_ucmr5.duckdb`.
- Asserts `source_nc_rows == loaded_nc_rows` and upserts `a1-epa-ucmr5-nc-ingest` in `proof-registry.json`.

### Step A2 — dbt Warehouse Build, Test & Static Docs
```bash
PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt build \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse

PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt docs generate \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse
```
- Commits `pfas_warehouse/target/{manifest.json,catalog.json,index.html,run_results.json}`.

### Step A3 — Apache Airflow 3.4.0 Clean Run & Prior-Period Backfill
```bash
export AIRFLOW_HOME=/home/antigravity/.airflow_home
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__DAGS_FOLDER=/home/antigravity/portfolio-factory/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False

.venv-airflow/bin/airflow db migrate
.venv-airflow/bin/airflow dags reserialize
.venv-airflow/bin/airflow dags list-import-errors

# Clean single-period run:
.venv-airflow/bin/airflow dags test pfas_ucmr5_pipeline 2026-11-01

# Prior-period backfill (Airflow 3 scheduler-managed):
.venv-airflow/bin/airflow backfill create \
  --dag-id pfas_ucmr5_pipeline \
  --from-date 2025-10-01 \
  --to-date 2025-10-01 \
  --max-active-runs 1 \
  --reprocess-behavior none
# Run api-server + scheduler briefly under LocalExecutor until summary appears:
# portfolio-factory/reports/pipeline_run_summary_2025-10-01.md
```
- Any failing `dbt test` exits non-zero, failing `dbt_test` and preventing `publish_run_summary` (`trigger_rule="all_success"`) from publishing.

### Step A4 — Advanced SQL Pack & Interactive HTML Dashboard
```bash
.venv/bin/python portfolio-factory/sql/run_sql_pack.py
.venv/bin/python portfolio-factory/dashboard/build_dashboard.py
```
- `04_incremental_merge_upsert.sql` executes against a scratch copy of DuckDB so marts remain untouched.
- Output dashboard: `portfolio-factory/dashboard/index.html` (zero external CDNs).

### Step A5 — Packet Claim-Verifier (Read-Only)
```bash
.venv/bin/python portfolio-factory/verifier/verify_packet.py \
  --packet <path_to_packet_dir_or_file> \
  --base-docs <path_to_base_resume> \
  --registry proof-registry.json \
  --jd <optional_jd_file_or_url> \
  --out-md /tmp/verify_report.md \
  --out-json /tmp/verify_report.json \
  --strict
```
- Verdicts: `FORBIDDEN`, `UNSUPPORTED`, `PROVEN_BY_ARTIFACT`, `IN_BASE_DOCS`, `DISAVOWED_HONEST_GAP`.

### Step A6 — Live Official Seed JD Capture & Gap Report
```bash
.venv/bin/python portfolio-factory/gap_analyser/capture_seed_jds.py
.venv/bin/python portfolio-factory/gap_analyser/gap_report.py
```
- Writes `portfolio-factory/reports/jd_gap_report.md` and `.json`.

## 4. Verification Checklist
```bash
.venv/bin/python -m shared.proof_registry validate
.venv/bin/pytest tests/test_build_a_*.py tests/test_proof_registry.py
```
Confirm all tests pass with `/home/antigravity/fixtures/` absent or ignored.
