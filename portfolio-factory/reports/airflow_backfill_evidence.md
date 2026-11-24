# Apache Airflow 3.4.0 Execution & Backfill Evidence (Build A3)

- **Owner / Legal Entity:** Temitope Soneye — *Tosson Services LLC dba Tosson Environmental Analytics*
- **Orchestrator:** `apache-airflow==3.4.0` (`LocalExecutor` on SQLite WAL, venv-isolated in `.venv-airflow/`)
- **DAG ID:** `pfas_ucmr5_pipeline` ([`dags/pfas_pipeline.py`](../dags/pfas_pipeline.py))
- **Task Graph:** `ingest_ucmr5 >> dbt_run >> dbt_test >> publish_run_summary` (`trigger_rule="all_success"`)
- **Retry Policy:** `retries=2`, `retry_delay=2m`, `retry_exponential_backoff=True`, `max_retry_delay=15m`
- **Import Errors:** `0` (`airflow dags list-import-errors` returned empty)

---

## 1. Commands Executed

```bash
export AIRFLOW_HOME=/home/antigravity/.airflow_home
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__DAGS_FOLDER=/home/antigravity/portfolio-factory/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False

# Initialize metadata DB & verify DAG bundle
.venv-airflow/bin/airflow db migrate
.venv-airflow/bin/airflow dags reserialize
.venv-airflow/bin/airflow dags list-import-errors

# 1. Clean end-to-end DAG run for logical date 2026-11-01
.venv-airflow/bin/airflow dags test pfas_ucmr5_pipeline 2026-11-01

# 2. Scheduler-managed prior-period backfill for logical date 2025-10-01
.venv-airflow/bin/airflow backfill create \
  --dag-id pfas_ucmr5_pipeline \
  --from-date 2025-10-01 \
  --to-date 2025-10-01 \
  --max-active-runs 1 \
  --reprocess-behavior none

# Executed by Airflow 3 api-server + scheduler under LocalExecutor
.venv-airflow/bin/airflow dags list-runs pfas_ucmr5_pipeline
```

---

## 2. Recorded Airflow 3 Run History (`airflow dags list-runs pfas_ucmr5_pipeline`)

```text
dag_id              | run_id                              | state   | run_after                        | logical_date              | start_date                       | end_date
====================+=====================================+=========+==================================+===========================+==================================+=================================
pfas_ucmr5_pipeline | manual__2026-11-24T00:29:49.019826+ | success | 2026-11-24T00:29:49.019826+00:00 | 2026-11-01T00:00:00+00:00 | 2026-11-24T00:29:49.086385+00:00 | 2026-11-24T00:30:38.500038+00:00
pfas_ucmr5_pipeline | backfill__2025-10-01T00:00:00+00:00 | success | 2025-10-01T00:00:00+00:00        | 2025-10-01T00:00:00+00:00 | 2026-11-24T00:30:55.469738+00:00 | 2026-11-24T00:31:50.635116+00:00
```

---

## 3. Verified Outputs & Quality Gates

- **Clean Run Report:** [`pipeline_run_summary_2026-11-01.md`](pipeline_run_summary_2026-11-01.md) — `68,633` EPA UCMR 5 NC rows reconciled (`==`), `291/291` NC PWSIDs mapped to SDWIS counties, `50/50` dbt tests passed (`0` errors).
- **Backfill Run Report:** [`pipeline_run_summary_2025-10-01.md`](pipeline_run_summary_2025-10-01.md) — executed via Airflow 3 `backfill__2025-10-01T00:00:00+00:00` under `LocalExecutor`, `68,633` rows reconciled with zero row duplication, `50/50` dbt tests passed.
- **Fail-Closed Test Gate:** Verified in `tests/test_build_a_airflow_dag.py` — injecting a negative analytical concentration causes `dbt test` to exit non-zero, failing `dbt_test` and blocking `publish_run_summary` (`trigger_rule="all_success"`) with zero silent report publish.

---

**Screening-Only Framing:** EPA UCMR 5 records are evaluated strictly against EPA's six 2024 PFAS drinking-water screening benchmarks for informational occurrence analysis only — never compliance determinations. EPA's rulemaking concerning potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards is **proposed / not final** (https://www.epa.gov/sdwa/proposed-pfas-rescission-rule; https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation).
