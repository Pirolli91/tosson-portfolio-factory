# Sprint 5 Implementation Plan — Job-Hunt Portfolio Factory (Build A) + Auction Intelligence v2 (Build B)

- **Date:** 2026-11-23
- **Owner:** Temitope Soneye (`Tosson Services LLC dba Tosson Environmental Analytics`)
- **Builder:** Antigravity (Gemini default; max 2 parallel agents post-approval)
- **Adjudicator / Operator:** Muse
- **Status:** **PLAN MODE — AWAITING MUSE ADJUDICATION** (No code written, no packages installed, no accounts created)

---

## 1. Standing Rules & Compliance Guardrails (Baked into Architecture & CI)

Every deliverable across the Shared Layer, Build A, and Build B enforces the owner's standing rules programmatically via automated pytest audit checks (`tests/test_workspace_audit.py`):

1. **Zero proprietary employer material:** Public EPA data only for Build A. Workspace audit fails if any forbidden employer-proprietary reference appears outside the explicit rule/blocklist definitions.
2. **Zero fabricated experience / precise claim language:** Every artifact runs end-to-end (dbt build+test green, Airflow DAG clean run + backfill green, row counts reconciled). Snowflake SQL is explicitly labelled **dialect-only (unexecuted)**; Power BI proof explicitly rests on the **DAX measure library + semantic-model spec** (no `.pbix` in Sprint 5).
3. **Read-only / zero external side effects:** Nothing submits applications, places bids, buys items, sends messages, or creates accounts (no Snowflake trial, no job-board accounts).
4. **UCMR 5 screening-only framing:** Occurrence/screening comparison against EPA 2024 MCL benchmarks ONLY — **never** a compliance or violation claim. Automated audit asserts the word `violation` never appears in dbt SQL/YAML/docs, DAX, HTML dashboard, reports, or READMEs. Legal attribution: `Tosson Services LLC dba Tosson Environmental Analytics`.
5. **Source-use policy (MASTER LAYER, 2026-11-02):** Every external dataset/source is public domain (EPA UCMR 5, EPA SDWIS, US Census, NHTSA vPIC/Recalls) or CC BY/CC0 verified on its own page, or cited with full canonical URL. Any unverifiable source is excluded and named as excluded. The prohibited boilerplate string referenced in `AGENTS.md` is forbidden across all outputs and checked by automated test.
6. **Zero secrets or PII:** Environment variable **names** only (`.env.example`), never values. Zero personal PII committed.
7. **Fixtures isolation & self-verifying tests:** Owner-staged `fixtures/` is strictly read-only, never modified, and excluded from the deliverable zip. The entire `pytest` suite passes with **no `fixtures/` directory present** via synthetic mini-fixtures under `tests/fixtures_synthetic/` and injectable CLI/module paths.
8. **Required runbooks:** One `SKILL.md` runbook per build at `.agents/skills/build-a-portfolio-factory/SKILL.md` and `.agents/skills/build-b-auction-intel-v2/SKILL.md`.

---

## 2. Target Hardware Constraints & Pinned Dependencies

### 2.1 EliteDesk Host Constraints
- **Target machine:** HP EliteDesk running **Linux Mint**, **32 GB RAM**, **no discrete GPU**.
- **Design choices driven by hardware:**
  - **Zero GPU / ML / heavy numeric stacks:** No PyTorch, TensorFlow, NumPy/SciPy, or Docker daemon required. Perceptual image hashing (B2) uses `Pillow` + Python stdlib only.
  - **Two venv-isolated Python 3.12 environments (zero system-wide installs):**
    1. `.venv/` — Core Build A (dbt + DuckDB + verifier + gap analyser) & Build B (Auction Intel v2).
    2. `.venv-airflow/` — Minimal Apache Airflow 3.4.0 installation (no-providers constraint file).
  - **Rationale for two venvs:** Eliminates transitive dependency conflicts (`pydantic`, `PyYAML`, `packaging`, `duckdb`, `sqlparse`) between `dbt-core` and `apache-airflow`, mirrors production task isolation, and keeps Airflow tasks calling `.venv/bin/python` and `.venv/bin/dbt` via subprocess (`check=True`).
  - **Resource footprint estimate:** Combined venvs ~350–450 MB disk; DuckDB NC warehouse ~15–25 MB; peak RAM during active Airflow + dbt run < 1.5 GB (well within 32 GB); 0 MB background RAM when idle.

### 2.2 Airflow Install Weight Strategy
- **Pinned minimal real Apache Airflow:** `apache-airflow==3.4.0` installed with Apache's official **no-providers** constraint file:
  `https://raw.githubusercontent.com/apache/airflow/constraints-3.4.0/constraints-no-providers-3.12.txt` (137 total packages vs 752 in full constraints; excludes Flask-AppBuilder, Celery, Kubernetes, and cloud providers).
- **Why Airflow 3.4.0 over 2.10.x on EliteDesk:** Airflow 3.x removed `SequentialExecutor` and added **native `LocalExecutor` support on SQLite (WAL mode)** — meaning real `LocalExecutor` runs locally with **zero PostgreSQL server and zero Docker overhead**. DAGs use modern Airflow 3 TaskFlow (`from airflow.sdk import dag, task`) and scheduler-managed backfills (`airflow backfill create`). We do **not** substitute any other orchestrator.

### 2.3 Exact Pinned Dependency Manifest (Verified on PyPI for Python 3.12)

#### Environment 1: `.venv/` (`requirements.txt`)
| Package | Exact Pin | Purpose | Build |
|---|---|---|---|
| Python | `3.12.x` (`3.12.16` in devbox; `3.12` on Mint) | Runtime | Shared / A / B |
| `dbt-core` | `==1.12.7` | dbt transformation & testing engine | A2, A3 |
| `dbt-duckdb` | `==1.11.1` | DuckDB adapter for dbt (supports native `MERGE`) | A2, A3 |
| `duckdb` | `==1.5.6` | Embedded OLAP warehouse (1.5.x line aligned with `dbt-duckdb==1.11.1`) | A1, A2, A4 |
| `python-docx` | `==1.2.0` | Parse `.docx` resumes, cover letters, and packets | A5, A6 |
| `lxml` | `==6.1.3` | XML backend required by `python-docx` (pinned explicitly) | A5, A6 |
| `Pillow` | `==13.0.0` | Image loading & 64-bit dHash perceptual hashing (no `imagehash`/`numpy`) | B2 |
| `requests` | `==2.34.2` | Public HTTP fetching (EPA UCMR 5, SDWIS, NHTSA vPIC/Recalls, seed JDs) | A1, A6, B3, B4 |
| `beautifulsoup4` | `==4.15.0` | HTML text extraction for live seed JDs & public parcel pages | A6, B3 |
| `jsonschema` | `==4.26.0` | Strict schema validation for `proof-registry.json` & JSON outputs | Shared, A, B |
| `PyYAML` | `==6.0.4` | Config/rules parsing (ROI thresholds, skill taxonomy, dbt YAML checks) | Shared, A, B |
| `pytest` | `==9.2.0` | Self-verifying test suite across Shared, Build A, and Build B | Shared, A, B |

#### Environment 2: `.venv-airflow/` (`requirements-airflow.txt`)
| Package | Exact Pin | Purpose | Build |
|---|---|---|---|
| `apache-airflow` | `==3.4.0` | Core orchestrator (`LocalExecutor` + SQLite WAL) | A3 |
| `apache-airflow-core` | `==3.4.0` | Airflow 3 core runtime (pinned explicitly) | A3 |
| `apache-airflow-task-sdk` | `==1.4.0` | Airflow 3 TaskFlow SDK (`airflow.sdk`) | A3 |
| Constraints URL | `constraints-3.4.0/constraints-no-providers-3.12.txt` | Pins all 137 transitive packages deterministically | A3 |

- **Node.js:** Not required (`0` packages). HTML dashboard (A4d) uses vanilla HTML/CSS/JS + inline SVG.

---

## 3. Workspace & Repository Layout

```text
/home/antigravity/
├── AGENTS.md                              # Read-only standing rules
├── SPRINT5-SPEC-2026-11-23.md             # Read-only sprint spec
├── implementation_plan.md                 # THIS PLAN
├── requirements.txt                       # Pinned .venv deps
├── requirements-airflow.txt               # Pinned .venv-airflow deps
├── proof-registry.json                    # Shared Proof Registry (built FIRST)
├── shared/
│   ├── __init__.py
│   ├── proof_registry.py                  # Schema validator + atomic read/write helper
│   └── schemas/
│       └── proof_registry.schema.json     # JSON Schema (Draft 2020-12)
├── portfolio-factory/                     # BUILD A — Git-ready hiring-manager repo
│   ├── README.md                          # Hiring-manager overview, proof map, exact runbook
│   ├── .gitignore
│   ├── .env.example                       # Variable NAMES only (zero values)
│   ├── ingest/
│   │   ├── ingest_ucmr5.py                # A1: repeatable EPA UCMR 5 + SDWIS county ingest
│   │   └── benchmarks_2024_mcl.csv        # EPA 2024 NPDWR screening benchmarks (public domain)
│   ├── warehouse/                         # Local DuckDB output (regenerable + reconciled)
│   ├── pfas_warehouse/                    # A2: dbt-core + dbt-duckdb project
│   │   ├── dbt_project.yml
│   │   ├── profiles.yml                   # Local relative DuckDB profile (no secrets)
│   │   ├── seeds/
│   │   │   └── epa_2024_pfas_benchmarks.csv
│   │   ├── models/
│   │   │   ├── staging/                   # stg_ucmr5_results, stg_pws_county_crosswalk, stg_pfas_benchmarks
│   │   │   ├── intermediate/              # int_ucmr5_pfas_screened, int_system_hazard_index
│   │   │   └── marts/                     # mart_county_scorecard, mart_analyte_summary, mart_system_screening
│   │   ├── tests/                         # Singular data tests (concentrations, arithmetic, reconciliation)
│   │   └── target/                        # Committed dbt docs generate output (manifest, catalog, index.html)
│   ├── dags/
│   │   └── pfas_pipeline.py               # A3: Airflow 3 TaskFlow DAG (LocalExecutor)
│   ├── reports/                           # A3 run summaries + backfill evidence logs
│   ├── sql/                               # A4a: 10 advanced SQL patterns + DuckDB verification runner
│   ├── snowflake/                         # A4b: Snowflake-dialect SQL + COPY/MERGE load script (DIALECT-ONLY)
│   ├── powerbi/                           # A4c: DAX measure library + semantic-model spec (no .pbix)
│   ├── dashboard/                         # A4d: Generator script + self-contained interactive HTML explorer
│   ├── verifier/                          # A5: verify_packet.py + skill_taxonomy.yaml + forbidden_rules.yaml
│   └── gap_analyser/                      # A6: gap_report.py + live seed JD capture & snapshot store
├── auction-intel-v2/                      # BUILD B — Read-only auction analytics modules
│   ├── README.md
│   ├── .env.example                       # Variable NAMES only
│   ├── INTEGRATION.md                     # B5: Mon/Wed/Fri & closing-<48h hook guide (non-invasive)
│   ├── config/
│   │   ├── roi_rules.yaml                 # B1 fee/margin/verdict band thresholds
│   │   └── land_criteria.yaml             # B3 county, acreage, cash/auction track, Mebane coords
│   ├── manifest_roi/                      # B1: Liquidation.com & B-Stock CSV parser + ROI engine
│   ├── hibid_churn/                       # B2: Snapshot diff, title similarity + Pillow dHash re-list detector
│   ├── land_scorer/                       # B3: Fail-closed NC land parcel scorer + direct-URL enforcer
│   └── kia_carnival/                      # B4: STRICTLY SEPARATE module (VIN decode, SC266, trim, KFA stub)
├── .agents/
│   └── skills/
│       ├── build-a-portfolio-factory/SKILL.md
│       └── build-b-auction-intel-v2/SKILL.md
├── tests/                                 # Self-verifying pytest suite (passes with NO fixtures/ dir)
│   ├── fixtures_synthetic/                # Mini EPA UCMR5, resume/packets, manifests, HiBid, parcels, VINs
│   ├── test_proof_registry.py
│   ├── test_build_a_ingest_dbt.py
│   ├── test_build_a_airflow_dag.py
│   ├── test_build_a_sql_bi.py
│   ├── test_build_a_verifier_gap.py
│   ├── test_build_b_manifest_roi.py
│   ├── test_build_b_hibid_churn.py
│   ├── test_build_b_land_scorer.py
│   ├── test_build_b_kia_carnival.py
│   └── test_workspace_audit.py            # Zero Progressive, zero "violation", zero secrets, zip hygiene
└── scripts/
    └── package_deliverable.sh             # Builds zip excluding fixtures/, .venv*, caches
```

---

## 4. Shared Layer — Proof Registry (Built FIRST)

- **File:** `proof-registry.json` (root) + `shared/proof_registry.py` + `shared/schemas/proof_registry.schema.json`.
- **Top-level fields:** `schema_version` (`"1.0.0"`), `updated_at` (ISO-8601 UTC), `owner` (`"Temitope Soneye"`), `legal_entity` (`"Tosson Services LLC dba Tosson Environmental Analytics"`), `entries` (array).
- **Per-entry contract (matches spec exactly):**
  ```json
  {
    "artifact_id": "a2-dbt-mart-county-scorecard",
    "kind": "dbt_model",
    "title": "NC County PFAS Screening Scorecard Mart",
    "repo_path": "portfolio-factory/pfas_warehouse/models/marts/mart_county_scorecard.sql",
    "evidence": {
      "command": "dbt build --profiles-dir . --project-dir portfolio-factory/pfas_warehouse",
      "result": "PASS (models=8, tests=24, errors=0)",
      "timestamp": "2026-11-23T18:00:00Z",
      "metrics": { "source_rows": 68633, "loaded_rows": 68633, "sha256": "..." }
    },
    "supports_claims": [
      "Built and tested a multi-layer dbt-core + DuckDB data warehouse on public EPA UCMR 5 PFAS data",
      "dbt",
      "DuckDB"
    ],
    "source_urls": [
      "https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule"
    ]
  }
  ```
- **Allowed `kind` enum:** `dbt_model | dag | sql_pack | dax_library | dashboard | report`.
- **Guarantees:**
  - `register_artifact()` validates against JSON Schema, verifies `repo_path` exists on disk, enforces non-empty `evidence.command/result/timestamp`, and writes atomically.
  - Both Build A and Build B write entries upon verified execution.
  - A5 (`verify_packet.py`) and A6 (`gap_report.py`) read **ONLY** `proof-registry.json` + base documents; any claim lacking both is `UNSUPPORTED` by construction.

---

## 5. Build A — Job-Hunt Portfolio Factory (`portfolio-factory/`)

### A1. Repeatable EPA UCMR 5 Ingest (`ingest/ingest_ucmr5.py`)
- **Public data source:** EPA UCMR 5 Occurrence Data Text Files (`https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule`, public domain; final dataset published August 2026). Uses the state-partitioned or full ZIP, extracting all `State = 'NC'` analytical records (`UCMR5_All*.txt`) and `UCMR5_ZIPCodes.txt`.
- **County enrichment (needed for `mart_county_scorecard`):** `UCMR5_All.txt` carries `PWSID` and `State` (plus ZIP codes in `UCMR5_ZIPCodes.txt`), not county name. Ingest fetches EPA's public-domain SDWIS NC water system geography (`https://data.epa.gov/efservice/GEOGRAPHIC_AREA/STATE_CODE/NC/JSON` or `WATER_SYSTEM`) to map `PWSID → CountyServed`, recording exact URL + checksum. Unmapped PWSIDs receive explicit `'UNMAPPED_COUNTY'` label (never silently dropped).
- **Reproducibility & reconciliation:**
  - CLI supports `--mode live` (downloads & caches raw zip under `warehouse/raw/`), `--input-file <path>` (repeatable re-run from cached/synthetic file), and `--db-path <path>`.
  - Computes SHA-256 checksum of source archive/extract, counts source NC lines vs DuckDB `raw_ucmr5.ucmr5_nc_results` rows, asserts exact equality (`source_row_count == loaded_row_count`), writes `raw_ucmr5.ingest_audit`, and updates `proof-registry.json` (`kind: "report"`).

### A2. dbt Project (`pfas_warehouse/`)
- **Stack:** `dbt-core==1.12.7` + `dbt-duckdb==1.11.1` + `duckdb==1.5.6`.
- **Layers & models:**
  - `seeds/epa_2024_pfas_benchmarks.csv`: 2024 EPA NPDWR MCL screening benchmarks in both `ppt (ng/L)` and `ug/L` (`PFOA=0.004 ug/L`, `PFOS=0.004 ug/L`, `PFHxS=0.010 ug/L`, `PFNA=0.010 ug/L`, `HFPO-DA=0.010 ug/L`, `PFBS_HBWC=2.0 ug/L` for Hazard Index `HI = 1.0`), with explicit regulatory-status footnote noting EPA's 2025/2026 proposed rescission of non-PFOA/PFOS rules.
  - `staging/`:
    - `stg_ucmr5_results` (typed concentrations in `ug/L` and `ppt`, detection flag from `AnalyticalResultsSign`, parsed collection date/year/quarter, `pwsid`, `contaminant`)
    - `stg_pws_county_crosswalk` (deduplicated NC `pwsid → county_name`, `size_category`)
    - `stg_pfas_benchmarks` (clean benchmark table)
  - `intermediate/`:
    - `int_ucmr5_pfas_screened` (joins analytical results to benchmarks, computes `benchmark_ratio = result_ppt / mcl_benchmark_ppt`, `above_mcl_benchmark_flag`, screening-only naming)
    - `int_system_hazard_index` (per-PWSID / collection-event mixture Hazard Index `SUM(conc_ppt / hbwc_ppt)` for HFPO-DA, PFBS, PFNA, PFHxS vs `1.0` benchmark)
  - `marts/`:
    - `mart_county_scorecard` — per NC county: systems monitored, total samples, detections (`>= MRL`), detection rate %, count/share of samples & systems above 2024 MCL screening benchmark, max concentration ratio, primary benchmark-exceeding analyte.
    - `mart_analyte_summary` — per analyte (29 PFAS + lithium): samples, systems tested, detections, detection rate %, P50/P90/max `ppt`, count above 2024 MCL benchmark (where applicable).
    - `mart_system_screening` — per NC water system (`PWSID`): county, population/size tier, analyte-level max & mean screening values vs 2024 MCL benchmarks, Hazard Index screening score & `above_hi_benchmark_flag`, screening status label (strictly screening language — zero `violation` wording).
- **Testing:**
  - Schema tests (`schema.yml`): `not_null`, `unique`, `accepted_values`, `relationships` across staging & marts.
  - Singular data tests (`tests/`): `assert_non_negative_concentrations.sql`, `assert_benchmark_arithmetic.sql` (verifies `ug/L * 1000 == ppt` and `benchmark_ratio` within `1e-6`), `assert_row_reconciliation.sql` (`COUNT(stg_ucmr5_results) == ingest_audit.loaded_rows`), `assert_hazard_index_bounds.sql`.
- **Documentation:** Run `dbt docs generate`, commit `target/manifest.json`, `target/catalog.json`, `target/index.html`, and document exact reproduction commands in `pfas_warehouse/README.md`. Register models in `proof-registry.json` (`kind: "dbt_model"`).

### A3. Airflow Orchestration (`dags/pfas_pipeline.py`)
- **Runtime:** `.venv-airflow/` (`apache-airflow==3.4.0`, `LocalExecutor`, SQLite WAL metadata DB at `AIRFLOW_HOME` inside a local non-zipped runtime path or repo-relative gitignored `.airflow_home/`).
- **DAG definition (`pfas_ucmr5_pipeline`):**
  - Schedule: `@monthly` (with `catchup=False`, `start_date=2025-01-01`, `max_active_runs=1`).
  - Default args: `retries=2`, `retry_delay=timedelta(minutes=2)`, `retry_exponential_backoff=True`, `execution_timeout=timedelta(minutes=15)`.
  - Task graph (`ingest_ucmr5 >> dbt_run >> dbt_test >> publish_run_summary`):
    1. `ingest_ucmr5`: invokes `.venv/bin/python portfolio-factory/ingest/ingest_ucmr5.py` with logical date (`ds`) metadata; returns row-count reconciliation dict via small XCom.
    2. `dbt_run`: invokes `.venv/bin/dbt run --project-dir ... --profiles-dir ...` (`subprocess.run(..., check=True)`).
    3. `dbt_test`: invokes `.venv/bin/dbt test --project-dir ... --profiles-dir ...` (`subprocess.run(..., check=True)`). Any test failure raises `CalledProcessError`, failing the task and halting the DAG.
    4. `publish_run_summary`: `trigger_rule="all_success"` (no silent publish on test failure). Queries DuckDB marts for run metrics (rows reconciled, dbt tests passed, top 10 NC screening counties) and writes one-page Markdown summary to `portfolio-factory/reports/run_summary_<ds>.md`.
- **Required evidenced runs (recorded in `proof-registry.json`, `kind: "dag"`):**
  1. One clean end-to-end run for the current period (`2026-11-01` or `2026-10-01`).
  2. One scheduler-managed backfill for a prior period (e.g., `2025-10-01` via `airflow backfill create`), producing its own dated run summary without duplicating warehouse rows.
  3. One negative verification test (in pytest) injecting a failing dbt test and asserting `publish_run_summary` is `upstream_failed` / skipped and never writes output.

### A4. SQL + BI Proof Pack
- **A4a. Advanced SQL (`portfolio-factory/sql/`):** 10 standalone `.sql` queries executed & verified against the DuckDB marts by a Python verification runner (`sql/run_sql_pack.py`), each with a standardized header naming the exact JD keyword(s) evidenced:
  1. `01_county_ranking_windows.sql` (`Window Functions`, `RANK / DENSE_RANK / PERCENT_RANK`)
  2. `02_sampling_gaps_and_islands.sql` (`Gaps-and-Islands`, `LAG / LEAD`, consecutive monitoring quarters)
  3. `03_rolling_quarterly_trend.sql` (`Moving Averages`, `ROWS BETWEEN` window frames)
  4. `04_incremental_merge_upsert.sql` (`Incremental MERGE`, SCD/idempotent upsert on DuckDB 1.5.6)
  5. `05_hazard_index_mixture_cohort.sql` (`Multi-Analyte CTE`, EPA Hazard Index mixture screening)
  6. `06_analyte_pivot_conditional_agg.sql` (`Conditional Aggregation / Pivoting`, county × PFAS matrix)
  7. `07_outlier_iqr_zscore_screening.sql` (`Statistical SQL`, `PERCENTILE_CONT`, IQR/z-score screening)
  8. `08_yoy_detection_rate_delta.sql` (`YoY Analytics`, period-over-period change with zero-division guards)
  9. `09_system_size_pareto_share.sql` (`Cumulative Share / Pareto`, `SUM() OVER` running totals)
  10. `10_data_quality_reconciliation.sql` (`Data Quality / Audit SQL`, orphan keys, null rates, source reconciliation)
- **A4b. Snowflake Dialect Pack (`portfolio-factory/snowflake/`):**
  - Translates the 3 mart queries + an incremental `COPY INTO` / internal stage / `MERGE` load script into valid Snowflake SQL (`VARIANT` metadata option, `QUALIFY`, `DATE_TRUNC`, `IFF`, `CREATE OR REPLACE STAGE`, `FILE FORMAT`).
  - Every file header, README section, and `proof-registry.json` claim string is explicitly tagged **`Snowflake-dialect SQL (dialect-only; not executed against a Snowflake account)`**.
- **A4c. Power BI Proof Pack (`portfolio-factory/powerbi/`):**
  - `measures.dax`: Reviewable DAX measure library organized into display folders (Screening Rates, Benchmark Ratios, Hazard Index, YoY Deltas, County Rankings, Dynamic Screening Labels) using `DIVIDE`, `CALCULATE`, `SAMEPERIODLASTYEAR`, `RANKX`, `SUMX`.
  - `semantic_model.md` + `model_spec.json`: Complete star-schema model spec (`fact_ucmr5_screening`, `dim_water_system`, `dim_county`, `dim_analyte_benchmark`, `dim_date`), cardinality (`*:1`), single-direction filters, sort-by columns, and explicit note that `.pbix` authoring is out of sprint scope (owner Windows follow-up).
- **A4d. Interactive HTML Dashboard (`portfolio-factory/dashboard/`):**
  - `build_dashboard.py` queries DuckDB marts and writes self-contained `dashboard/index.html` (zero external CDN dependencies required to render; inline JSON data + responsive CSS + vanilla JS interactive SVG charts + sortable county/system screening table + analyte filter + county search + prominent UCMR 5 screening-vs-benchmark disclaimer and Tosson Services LLC dba Tosson Environmental Analytics footer).

### A5. Packet Claim-Verifier (`portfolio-factory/verifier/verify_packet.py`)
- **Inputs:** `--jd <file_or_url>`, `--packet <file_or_dir>` (supports `.docx`, `.txt`, `.md`), `--registry <proof-registry.json>`, `--base-docs <dir_or_files>` (injectable; defaults to `fixtures/` if present, never fails tests when absent).
- **Deterministic claim extraction & verification:**
  - Curated `skill_taxonomy.yaml` mapping canonical skills/tools/experience phrases + aliases (e.g., `dbt`, `Apache Airflow`, `Snowflake`, `Power BI`, `DAX`, `DuckDB`, `SQL`, `EDI`, `Python`, `PFAS / UCMR 5`, etc.) plus claim-strength qualifiers (e.g., distinguishing `"Snowflake-dialect SQL"` vs `"production Snowflake administration"`).
  - Curated `forbidden_rules.yaml` catching forbidden claims: US citizenship / security clearance overclaims, employer-proprietary references (including Progressive Insurance identifiers), fabricated production deployments, and UCMR 5 "violation" language.
  - Verdict logic per extracted claim (strict precedence):
    1. `FORBIDDEN` — matches forbidden-claim rule.
    2. `PROVEN_BY_ARTIFACT` — matches exact or normalized `supports_claims` in `proof-registry.json` (emits `artifact_id` + evidence summary).
    3. `IN_BASE_DOCS` — evidenced in owner's base resume / cover letter (emits matched file + snippet).
    4. `UNSUPPORTED` — present in packet, absent from both registry and base docs (flagged: must remove or soften).
  - **Absence check:** Also reports JD-requested skills cleanly omitted from packet (confirming honest omission — e.g., `evermore` omitting dbt/Airflow = PASS).
- **Outputs:** Claim-by-claim report in Markdown (`--out-md`) and JSON (`--out-json`).
- **Tests:**
  - Synthetic packet with planted unsupported claims (e.g., Kubernetes, Terraform, EDI X12, fabricated Snowflake production warehouse) + planted forbidden claim → 100% caught.
  - Synthetic clean packet (matching synthetic base resume + registry) → 0 unsupported, 0 forbidden.
  - When owner-staged `fixtures/packets/` + `fixtures/base-resume.docx` are present locally: optional CLI run verifies `evermore` packet passes as-submitted.

### A6. JD Gap Analyser (`portfolio-factory/gap_analyser/gap_report.py`)
- **Live seed JD capture (`capture_seed_jds.py`):** At build time, fetches official career pages ONLY (never aggregators, never reconstructed from memory):
  1. Centene Data Analyst III (`1672733-1`)
  2. Genworth / CareScout Data Analyst (`REQ-260438`)
  3. Bureau Veritas Senior Sustainability Consultant (`214408`)
  Records canonical URL, HTTP status, UTC capture timestamp, and status (`OPEN` with captured text, `CLOSED` if 404/closed notice, or `UNFETCHABLE_BOT_GATE` if blocked by anti-bot challenge — never bypassing challenges).
- **Gap scoring:** Extracts required & preferred skills using the shared `skill_taxonomy.yaml`, diffs against `proof-registry.json` + base docs, computes `gap_score = frequency * target_role_weight`, and outputs ranked gaps (`.md` + `.json`) showing covered-by-artifact, covered-by-base-docs, and true remaining gaps.

---

## 6. Build B — Auction Intelligence v2 (`auction-intel-v2/`)

Read-only analytics extending `auctions.tossonanalytics.com` (Mon/Wed/Fri cadence) with **zero modification** to existing live dashboard behaviour and **zero bidding/buying/account actions**.

### B1. Manifest ROI Analyser (`manifest_roi/`)
- **Format adapters:** Pluggable CSV adapters for `liquidation_com` and `bstock` (auto-detects or `--format` flag; handles currency strings, header aliases, missing optional columns).
- **Landed cost arithmetic (shown explicitly per lot):**
  - `lot_bid_price` + `buyers_premium` (`lot_bid_price * premium_rate`) + `shipping_estimate` + `handling_or_tax` = `landed_cost`.
- **Resale-comp engine (explicit mode labelling):**
  - `OWNER_SOLD_HISTORY` mode: when `--sold-history` (or `fixtures/sold-history.csv`) is present, matches manifest items via normalized token similarity to compute empirical low/mid/high resale comps from Temitope's Facebook Marketplace history.
  - `PUBLIC_COMP_FALLBACK` mode: when sold history is absent (or for unmatched items), applies transparent, documented condition-tier recovery multipliers against MSRP/unit retail minus selling fees & defect allowance. Every output header explicitly prints active mode (`OWNER_SOLD_HISTORY`, `HYBRID`, or `PUBLIC_COMP_FALLBACK`).
- **Verdict bands (`config/roi_rules.yaml`):** Computes `net_profit = net_resale_mid - landed_cost` and `roi_pct = net_profit / landed_cost`, assigning `STRONG` / `MARGINAL` / `PASS` with full line-item arithmetic in Markdown + JSON so Muse's hand-checked sample lot reconciles to the penny.

### B2. HiBid Churn Tracker (`hibid_churn/`)
- **Inputs:** Two chronological refresh snapshot files (`--prev`, `--curr`, JSON or CSV) + optional `--categories` watch filter + optional local image cache directory.
- **Re-list detection:**
  - Text similarity: normalized title (lowercased, stripped lot numbers/punctuation) combining token Jaccard + `difflib.SequenceMatcher` ratio.
  - Visual similarity: 64-bit difference hash (**dHash**) computed with `Pillow==13.0.0` (`Image.convert("L").resize((9, 8))`) + Hamming distance (`<= 10` bits = visual match). Gracefully degrades to text-only when image is unavailable, logging `match_method` (`TITLE_AND_IMAGE`, `TITLE_ONLY`, `IMAGE_ONLY`).
- **Cycle classification:** `NEW`, `RELISTED` (with `prior_lot_id`, similarity score, Hamming distance, price delta), `PRICE_UP`, `PRICE_DOWN`, `UNCHANGED`, `DROPPED`.
- **Outputs:** Churn report (`.md` + `.json`). Pytest includes a planted re-listed lot across synthetic snapshots and verifies detection.

### B3. Land Parcel Scorer (`land_scorer/`)
- **Owner criteria (`config/land_criteria.yaml`):**
  - Counties: `Caswell`, `Rockingham`, `Person` (NC only).
  - Acreage: `1.0 <= acreage <= 5.0`.
  - Tracks: `CASH_TRACK` (`price < 30000`) and `AUCTION_TRACK` (`price <= 5000`, subset flagged distinctly).
  - Reference point: Mebane, NC (`36.0960, -79.2670`) — Haversine distance when coordinates present (optional factor; missing coordinates reduce confidence/score without fabricating).
- **Fail-closed enforcement:** Any record missing `price` or `acreage` (null, empty, `<= 0`, non-numeric) or failing county/acreage/price bounds is **excluded** and tallied in `excluded_summary` by exact reason — never estimated or imputed.
- **Direct URL enforcement (standing rule):** Every emitted find must carry a validated direct listing/parcel URL. Search-page URLs (matching `/search`, `?q=`, `search_results`, etc.) are rejected and replaced with literal `"URL not captured"`. If no direct URL exists, literal `"URL not captured"` is emitted.
- **Sources:** Public county GIS / tax-auction feed adapters (read-only) + injectable CSV/JSON loader for offline/synthetic runs.

### B4. Kia Carnival Checker (`kia_carnival/` — STRICTLY SEPARATE MODULE)
- **Isolation guarantee:** Zero imports between `kia_carnival/` and `manifest_roi/`, `hibid_churn/`, or `land_scorer/` (enforced by an AST import-isolation test in `tests/test_build_b_kia_carnival.py`). Monitor mode only.
- **Components:**
  1. **VIN Decoder:** Calls public NHTSA vPIC API (`https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/<VIN>?format=json`) via injectable HTTP client (mocked in offline pytest). Verifies `Make == KIA`, `Model == Carnival`, `ModelYear >= 2022`.
  2. **NHTSA Recall & SC266 Checker:** Calls public NHTSA Recalls API (`https://api.nhtsa.gov/recalls/recallsByVehicle?make=kia&model=carnival&modelYear=<YEAR>`) to detect Kia `SC266` / NHTSA `23V144000` (power sliding door) applicability, AND accepts an optional VIN-level recall status feed/fixture to flag `SC266_OPEN` vs `SC266_COMPLETED` vs `SC266_VERIFY_VIN` (always emitting direct URL `https://www.nhtsa.gov/recalls?vin=<VIN>`).
  3. **Trim Filter:** Parses decoded VIN trim + listing title/description. `EX` and `SX` (8-passenger) → `PASS`; `SX Prestige`, `VIP Lounge`, `VIP Lounge Seat Package`, `7-passenger lounge` → `FLAGGED_OUT_VIP_LOUNGE`; unknown → `MANUAL_TRIM_CHECK`.
  4. **Summer-2027 KFA Finance-Clause Scanner Stub:** Parses optional finance contract text (or generates a pre-signing checklist) checking for: (a) no minimum financing term / early-payoff restriction, (b) explicit `$0` / no prepayment penalty clause, (c) simple-interest daily accrual verification, (d) dealer chargeback vs borrower rebate-clawback distinction.

### B5. Runbook + Integration Notes (`INTEGRATION.md` + `.agents/skills/build-b-auction-intel-v2/SKILL.md`)
- Documents non-invasive sidecar integration into the existing Mon/Wed/Fri refresh and closing-`<48h` alert pipeline for `auctions.tossonanalytics.com` (read-only consumption of existing snapshot exports, separate output paths, cron/systemd examples, env var **names** only).
- Explicitly documents B4's standalone invocation schedule (never bundled into general auction batch).

---

## 7. Verification Plan & Exit Gate Mapping

| Gate | Automated Verification | Pass Criterion |
|---|---|---|
| Shared Registry | `pytest tests/test_proof_registry.py` | Valid JSON Schema; all `repo_path` exist; every `supports_claims` traceable to runnable artifact |
| A1 + A2 (Ingest + dbt) | `ingest_ucmr5.py` + `dbt build` + `dbt docs generate` + `pytest tests/test_build_a_ingest_dbt.py` | Live NC EPA row count reconciled (`==`), all dbt models/tests green, zero `violation` strings |
| A3 (Airflow) | `.venv-airflow` clean run + prior-period backfill + `pytest tests/test_build_a_airflow_dag.py` | Clean run & backfill summaries generated; dbt test failure blocks `publish_run_summary` |
| A4 (SQL + BI) | `sql/run_sql_pack.py` + `build_dashboard.py` + `pytest tests/test_build_a_sql_bi.py` | 10/10 SQL patterns execute cleanly; Snowflake tagged dialect-only; DAX/model spec & HTML valid |
| A5 (Verifier) | `pytest tests/test_build_a_verifier_gap.py` + optional local `evermore` run | 100% synthetic planted claims caught; `evermore` passes as-submitted when staged |
| A6 (Gap Report) | `capture_seed_jds.py` + `gap_report.py` + pytest | All 3 seed JDs captured live (or `CLOSED` dated); ranked gap report produced |
| B1 (Manifest ROI) | `pytest tests/test_build_b_manifest_roi.py` + sample lot hand-check | Arithmetic & verdict match Muse's hand calculation; fallback mode explicitly labelled |
| B2 (HiBid Churn) | `pytest tests/test_build_b_hibid_churn.py` | Planted re-list caught via title similarity + Pillow dHash; deltas accurate |
| B3 (Land Scorer) | `pytest tests/test_build_b_land_scorer.py` | Only criteria-passing parcels emitted; missing price/acreage fail-closed; direct URL or `"URL not captured"` |
| B4 (Kia Carnival) | `pytest tests/test_build_b_kia_carnival.py` | Flags VIP Lounge trim + SC266-open VIN; AST confirms total isolation from B1–B3 |
| Audit & Packaging | `pytest tests/test_workspace_audit.py` + `scripts/package_deliverable.sh` | Full suite passes with NO `fixtures/`; zero proprietary/PII/secret leaks; zip excludes `fixtures/` |

---

## 8. Execution Sequencing (Post-Adjudication Only)

1. **Step 0 (Sequential):** Create `.venv/` and `.venv-airflow/` with exact pinned versions; verify imports and CLI versions.
2. **Step 1 (Sequential):** Build Shared Proof Registry (`shared/`, schema, `proof-registry.json`).
3. **Step 2 (Up to 2 parallel agents — Gemini default):**
   - **Agent 1 (Build A):** A1 Ingest → A2 dbt + docs → A3 Airflow clean run & backfill → A4 SQL/Snowflake/PowerBI/Dashboard → A5 Verifier → A6 Gap Analyser + Build A `SKILL.md`.
   - **Agent 2 (Build B):** B1 Manifest ROI → B2 HiBid Churn → B3 Land Scorer → B4 Kia Carnival (isolated) → B5 Integration Notes + Build B `SKILL.md`.
4. **Step 3 (Sequential):** Register all verified outputs in `proof-registry.json`, run full `pytest` suite (confirming zero dependency on `fixtures/`), run workspace audit, and build deliverable zip (excluding `fixtures/` and venvs).

---

## 9. Open Decisions & Flags for Muse's Adjudication

Please adjudicate each item below (recommended defaults are marked **[Recommended]**):

| ID | Topic | Issue / Unresolved Detail | Recommended Resolution |
|---|---|---|---|
| **D1** | **EliteDesk Venv Layout** (Linux Mint, 32GB RAM, no GPU) | Combining `dbt-core==1.12.7` and `apache-airflow==3.4.0` in one venv risks transitive version clashes (`pydantic`, `PyYAML`, `packaging`, `duckdb`). | **[Recommended]** Use two isolated venvs (`.venv/` for dbt + Build A/B; `.venv-airflow/` for Airflow), zero Docker/GPU, ~400 MB disk, <1.5 GB peak RAM. |
| **D2** | **Airflow Version & Install Weight** | Airflow 2.10.x requires PostgreSQL to run `LocalExecutor` (SQLite only supported `SequentialExecutor`), whereas **Airflow 3.4.0** supports `LocalExecutor` natively on SQLite WAL mode and ships a 137-package `constraints-no-providers-3.12.txt`. | **[Recommended]** Pin `apache-airflow==3.4.0` + `constraints-no-providers-3.12.txt` + `LocalExecutor` on SQLite WAL (real Airflow, zero Postgres/Docker weight). |
| **D3** | **Owner-Staged `fixtures/` Expectations** | No `fixtures/` directory is currently staged in this workspace (expected for build-time isolation). Need confirmation of expected local filenames/schemas on EliteDesk for shadow run: (a) `fixtures/base-resume.docx` (+ optional `base-cover-letter.docx`); (b) `fixtures/packets/{evermore,centene-1673175,viva-npilda187}/`; (c) `fixtures/sold-history.csv` (`item,cost,sold_price`); (d) `fixtures/manifests/*.csv` (Liquidation.com / B-Stock samples for B1 hand-check). | **[Recommended]** Confirm these paths/column names (or provide any exact header names Muse uses in shadow run); all CLI tools will accept injectable paths and header aliases, and tests will run 100% without `fixtures/`. |
| **D4** | **UCMR 5 August 2026 Final Release Row Count & County Join** | EPA published the final UCMR 5 dataset in August 2026, so live NC row count may differ from the spec's `~68,633` figure. Additionally, `UCMR5_All.txt` lacks a `County` column (has `PWSID`, `State`, and companion `UCMR5_ZIPCodes.txt`). | **[Recommended]** Reconcile dynamically against the live EPA download (logging exact URL, UTC date, SHA-256, and row count in `proof-registry.json`) and join EPA's public-domain SDWIS NC `PWSID → County` table (with explicit `UNMAPPED_COUNTY` for any unmatched PWSIDs). |
| **D5** | **2024 MCL Benchmarks vs 2025/2026 Rescission Context** | Spec requires 2024 MCL benchmarks (`PFOA/PFOS 4 ppt`, `PFHxS/PFNA/HFPO-DA 10 ppt`, `Hazard Index 1.0`). In May 2025–Oct 2026 EPA proposed rescinding the non-PFOA/PFOS standards while keeping PFOA/PFOS. | **[Recommended]** Implement all six 2024 benchmarks as specified (screening-only framing) AND add a concise regulatory-status footnote citing EPA's 2025/2026 rescission rulemaking for domain accuracy. |
| **D6** | **B1 ROI Verdict Thresholds & Default Fees** | Spec does not fix exact `STRONG` / `MARGINAL` / `PASS` cutoffs or default shipping/buyer's-premium rates. | **[Recommended]** Parameterize in `config/roi_rules.yaml` with defaults: `STRONG` (ROI ≥ 40% and net profit ≥ \$150), `MARGINAL` (15% ≤ ROI < 40% and net profit > \$0), `PASS` (ROI < 15% or net profit ≤ \$0); 10% buyer's premium default when absent from manifest. Confirm or supply Muse's exact cutoffs for hand-check alignment. |
| **D7** | **B2 HiBid Snapshot Schema** | Live `auctions.tossonanalytics.com` scraper JSON/CSV column names are not in this workspace. | **[Recommended]** Define a clean canonical snapshot schema (`lot_id, title, category, current_bid, url, image_path, snapshot_ts`) plus a field-mapping config so B5 documents exact drop-in wiring without modifying live code. Provide real column names if Muse wants 1:1 pre-mapping. |
| **D8** | **B3 NC County Land Feed URLs** | Public tax-auction / GIS listing formats differ across Caswell, Rockingham, and Person counties, and third-party real estate portals often gate automated fetches with anti-bot challenges (which we will not bypass). | **[Recommended]** Build clean adapters for public county/auction CSV & HTML feeds plus injectable local input, enforcing fail-closed validation and direct-URL rules. Confirm any preferred public county URLs Muse wants pre-configured. |
| **D9** | **B4 NHTSA VIN-Level Open Recall Limitation** | NHTSA's public JSON API (`api.nhtsa.gov/recalls/recallsByVehicle`) returns recalls by Make/Model/Year (catching `SC266` / `23V144000` for 2022–2023 Carnivals), whereas VIN-specific open/remedied status is web/CAPTCHA-gated. | **[Recommended]** Combine live vPIC VIN decode + live model-year NHTSA SC266 check + injectable VIN-status record adapter (so test fixtures deterministically trigger `SC266_OPEN`) + direct `https://www.nhtsa.gov/recalls?vin=<VIN>` link when VIN-level remedy status requires manual confirmation. |
| **D10** | **A6 Seed JD Weights & Bot-Gated Career Portals** | Official career portals (Workday/SuccessFactors for Centene, Genworth/CareScout, Bureau Veritas) occasionally render via JS or anti-bot gates. Target-role weights are also unspecified. | **[Recommended]** Default role weights (`Data Analyst = 1.0`, `Sustainability Consultant = 0.7`, configurable in YAML). Record live HTTP status cleanly: `OPEN`, `CLOSED` (with capture date), or `UNFETCHABLE_BOT_GATE` (never bypassing challenges or reconstructing from aggregators/memory). |
| **D11** | **DuckDB Exact Pin (`1.5.6` vs `2.0.1`)** | `duckdb==2.0.1` is latest on PyPI, while `dbt-duckdb==1.11.1` aligns its MotherDuck extra with `1.5.x` and supports native `MERGE` from `1.4.0+`. | **[Recommended]** Pin `duckdb==1.5.6` for guaranteed stability with `dbt-duckdb==1.11.1` (still gives native `MERGE` for A4a). |

---

**STOP:** Plan complete. Awaiting Muse's adjudication on **D1–D11** before creating venvs, installing packages, or writing any code.
