# North Carolina PFAS Data Warehouse & Job-Hunt Portfolio Factory (`portfolio-factory/`)

**Owner / Legal Entity:** Temitope Soneye — *Tosson Services LLC dba Tosson Environmental Analytics*  
**Data Source:** 100% public-domain U.S. EPA UCMR 5 North Carolina occurrence data (`68,633` analytical results across `291` NC public water systems and `92` counties) + public-domain U.S. EPA SDWIS NC county geography.

---

## What This Repository Proves (Hiring-Manager Map)

Every technical capability below is backed by runnable code, passing tests, and reconciled outputs recorded in [`../proof-registry.json`](../proof-registry.json):

| Capability | Artifact | Verified Evidence |
|---|---|---|
| **Repeatable Data Ingestion & Reconciliation** | [`ingest/ingest_ucmr5.py`](ingest/ingest_ucmr5.py) | Streams live public EPA UCMR 5 ZIP + EPA SDWIS NC county CSVs into DuckDB; SHA-256 checksums + exact row reconciliation (`68,633 == 68,633`, `291/291` NC PWSIDs mapped; explicit `UNMAPPED_COUNTY` fallback). |
| **dbt-core + DuckDB Data Warehouse** | [`pfas_warehouse/`](pfas_warehouse/) | 3-layer warehouse (`staging` -> `intermediate` -> `marts`: `mart_county_scorecard`, `mart_analyte_summary`, `mart_system_screening`), 1 seed (`epa_2024_pfas_benchmarks`), 8 models, **50 passing schema & singular data tests**, and generated static dbt docs ([`pfas_warehouse/target/index.html`](pfas_warehouse/target/index.html)). |
| **Apache Airflow 3 Orchestration (`LocalExecutor`)** | [`dags/pfas_pipeline.py`](dags/pfas_pipeline.py) | Real Apache Airflow 3.4.0 TaskFlow DAG (`pfas_ucmr5_pipeline`) with retries + exponential backoff, fail-closed `dbt test` gate (`trigger_rule="all_success"`), evidenced clean run ([`reports/pipeline_run_summary_2026-11-01.md`](reports/pipeline_run_summary_2026-11-01.md)), and prior-period backfill ([`reports/pipeline_run_summary_2025-10-01.md`](reports/pipeline_run_summary_2025-10-01.md), [`reports/airflow_backfill_evidence.md`](reports/airflow_backfill_evidence.md)). |
| **Advanced Analytical SQL (10 Patterns)** | [`sql/`](sql/) & [`sql/run_sql_pack.py`](sql/run_sql_pack.py) | 10 standalone `.sql` queries (window ranking, gaps-and-islands, 3-quarter rolling frames, DuckDB 1.5 native `MERGE` upsert, Hazard Index mixture cohort, analyte pivot, Tukey IQR/z-score outliers, YoY deltas, Pareto cumulative share, end-to-end reconciliation) — all 10 executed and verified non-empty. |
| **Snowflake-Dialect SQL (Dialect-Only)** | [`snowflake/`](snowflake/) | Idiomatic Snowflake-dialect translations of all 3 marts + `STAGE`/`FILE FORMAT`/`COPY INTO`/`VARIANT`/`MERGE` load script. **Explicitly labelled dialect-only (not executed against a Snowflake account).** |
| **Power BI (DAX & Semantic Model Spec)** | [`powerbi/`](powerbi/) | 20 reviewable DAX measures ([`powerbi/measures.dax`](powerbi/measures.dax)) across 6 display folders + 5-table star-schema specification ([`powerbi/semantic_model.md`](powerbi/semantic_model.md), [`powerbi/model_spec.json`](powerbi/model_spec.json)). **No `.pbix` in this sprint** (Windows Power BI Desktop follow-up). |
| **Interactive Visual Dashboard** | [`dashboard/index.html`](dashboard/index.html) | Self-contained interactive HTML/SVG County & System PFAS Screening Explorer rendered directly from the DuckDB marts via [`dashboard/build_dashboard.py`](dashboard/build_dashboard.py) (zero external CDN dependencies). |
| **Packet Claim-Verifier** | [`verifier/verify_packet.py`](verifier/verify_packet.py) | Deterministic `.docx`/`.txt`/`.md` claim audit with honest-candor disavowal awareness (`DISAVOWED_HONEST_GAP`) and standing-rule forbidden-claim guards (`FORBIDDEN`, `PROVEN_BY_ARTIFACT`, `IN_BASE_DOCS`, `UNSUPPORTED`). Read-only; never submits. |
| **JD Skill Gap Analyser** | [`gap_analyser/`](gap_analyser/) | Live official-career-page JD capture (never bypassing anti-bot gates or reconstructing closed postings from memory) + weighted gap scoring ([`reports/jd_gap_report.md`](reports/jd_gap_report.md)). |

---

## Exact Commands to Reproduce

All dependencies are venv-isolated (`.venv/` for core + dbt + DuckDB; `.venv-airflow/` for Apache Airflow 3.4.0). From the workspace root:

```bash
# 1. Ingest live public EPA UCMR 5 NC occurrence data + SDWIS counties into DuckDB
.venv/bin/python portfolio-factory/ingest/ingest_ucmr5.py

# 2. Build dbt warehouse (seed + 8 models + 50 tests) and generate static dbt docs
PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt build \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse

PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt docs generate \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse

# 3. Execute and verify all 10 advanced SQL patterns against DuckDB marts
.venv/bin/python portfolio-factory/sql/run_sql_pack.py

# 4. Render the self-contained interactive HTML dashboard
.venv/bin/python portfolio-factory/dashboard/build_dashboard.py

# 5. Execute the Apache Airflow 3 DAG (LocalExecutor + SQLite WAL)
export AIRFLOW_HOME=/home/antigravity/.airflow_home
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__DAGS_FOLDER=/home/antigravity/portfolio-factory/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
.venv-airflow/bin/airflow db migrate
.venv-airflow/bin/airflow dags test pfas_ucmr5_pipeline 2026-11-01

# 6. Run Claim-Verifier (A5) and JD Gap Analyser (A6)
.venv/bin/python portfolio-factory/gap_analyser/capture_seed_jds.py
.venv/bin/python portfolio-factory/gap_analyser/gap_report.py

# 7. Run self-verifying pytest suite (passes with NO fixtures/ folder present)
.venv/bin/pytest tests/test_build_a_*.py tests/test_proof_registry.py
```

---

## Screening-Only Disclaimer & Regulatory-Status Footnote

- **UCMR 5 Screening-Only Framing:** EPA's Fifth Unregulated Contaminant Monitoring Rule (UCMR 5) collects occurrence data for unregulated contaminants. All comparisons in this repository against EPA's 2024 drinking-water benchmarks (`PFOA 4 ppt`, `PFOS 4 ppt`, `PFHxS 10 ppt`, `PFNA 10 ppt`, `HFPO-DA 10 ppt`, and the 4-PFAS mixture Hazard Index `1.0` using HBWCs `HFPO-DA=10`, `PFNA=10`, `PFHxS=10`, `PFBS=2,000 ppt`) are strictly **informational occurrence screening analyses** and never regulatory compliance determinations.
- **Regulatory-Status Footnote (Proposed / Not Final):** All six 2024 EPA PFAS National Primary Drinking Water Regulation (NPDWR) screening benchmarks from the April 26, 2024 final rule ([89 FR 32532](https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation)) are implemented here. EPA has initiated a **proposed / not final** rulemaking regarding potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards while retaining PFOA and PFOS ([EPA Proposed PFAS Rescission Rule](https://www.epa.gov/sdwa/proposed-pfas-rescission-rule)).
- **Public-Domain Sources:**
  - EPA UCMR 5 Occurrence Data: https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule
  - EPA Envirofacts SDWIS Geographic Area (NC): https://data.epa.gov/efservice/GEOGRAPHIC_AREA/PRIMACY_AGENCY_CODE/NC/PWS_TYPE_CODE/CWS/CSV
  - 2024 EPA PFAS NPDWR (89 FR 32532): https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation
  - EPA Proposed PFAS Rescission Rule (proposed / not final): https://www.epa.gov/sdwa/proposed-pfas-rescission-rule

*Read-only portfolio & analytics tooling by **Tosson Services LLC dba Tosson Environmental Analytics**. Nothing in this repository submits applications, creates accounts, or sends external communications.*
