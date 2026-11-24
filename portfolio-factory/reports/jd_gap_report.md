# JD Skill Gap Analysis Report (Build A6)

- **Generated (UTC):** 2026-11-24T00:28:09Z
- **Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Seed JDs Evaluated:** 3 (`OPEN=1`, `CLOSED=0`, `UNFETCHABLE_BOT_GATE=2`)

## Live Seed JD Capture Status (Official Employer Career Pages Only)

| JD ID | Company | Role | Req ID | Weight | HTTP | Status | Captured (UTC) | Official URL |
|---|---|---|---|---:|---:|---|---|---|
| `bureau-veritas-214408` | Bureau Veritas | Senior Sustainability Consultant | `214408` | 0.7 | 200 | `OPEN` | 2026-11-24T00:28:07Z | https://careers.bureauveritas.com/job/Senior-Sustainability-Consultant/214408-en_US/ |
| `centene-1672733-1` | Centene Corporation | Data Analyst III | `1672733-1` | 1.0 | 403 | `UNFETCHABLE_BOT_GATE` | 2026-11-24T00:28:07Z | https://jobs.centene.com/us/en/jobs/1672733-1/ |
| `genworth-carescout-req-260438` | Genworth / CareScout | Data Analyst | `REQ-260438` | 1.0 | 429 | `UNFETCHABLE_BOT_GATE` | 2026-11-24T00:28:07Z | https://gnw.wd1.myworkdayjobs.com/en-US/GNW/job/Data-Analyst_REQ-260438 |

*Standing rule note: Postings gated by Cloudflare/Workday anti-bot challenges or rate limits are recorded honestly as `UNFETCHABLE_BOT_GATE` (never bypassed and never reconstructed from memory or aggregators). Closed postings are recorded as `CLOSED` with UTC capture date.*

## Ranked Skills & Remaining Gaps (`gap_score = frequency × target_role_weight`)

| Rank | Skill | Category | Freq | Demand Score | Gap Score | Coverage | Evidence | JDs |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | ESG / GHG / Sustainability Reporting | sustainability_domain | 1 | 0.70 | 0.70 | `TRUE_GAP` | Not present in proof-registry.json or base documents | bureau-veritas-214408 |
| 2 | R | programming | 1 | 0.70 | 0.70 | `TRUE_GAP` | Not present in proof-registry.json or base documents | bureau-veritas-214408 |
| 3 | Power BI | bi_visualization | 1 | 0.70 | 0.00 | `COVERED_BY_ARTIFACT` | a4c-powerbi-dax-semantic-model: Power BI (DAX measure library and star-schema semantic model specification; no .pbix in Sprint 5) | bureau-veritas-214408 |
| 4 | Python | programming | 1 | 0.70 | 0.00 | `COVERED_BY_ARTIFACT` | a1-epa-ucmr5-nc-ingest: Built repeatable Python + DuckDB ingestion pipeline for public EPA UCMR 5 North Carolina occurrence data with SHA-256 checksums and exact row reconciliation | bureau-veritas-214408 |
| 5 | SQL | data_engineering | 1 | 0.70 | 0.00 | `COVERED_BY_ARTIFACT` | a2-dbt-mart-analyte-summary: SQL | bureau-veritas-214408 |

