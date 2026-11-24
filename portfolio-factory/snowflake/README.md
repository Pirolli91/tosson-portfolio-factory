# Snowflake-Dialect SQL Pack (Build A4b)

> **Important Scope & Claim-Precision Label:**  
> **Snowflake-dialect SQL (dialect-only; not executed against a Snowflake account).**  
> Per Sprint 5 standing rules, no Snowflake trial or cloud account was created during this sprint. All executable warehouse logic runs and is tested locally on DuckDB in [`pfas_warehouse/`](../pfas_warehouse/) and [`sql/`](../sql/). This directory provides idiomatic Snowflake-dialect translations of the three dbt marts plus an incremental stage/`COPY INTO`/`MERGE` load pattern.

**Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics

## Files

| File | Snowflake-Specific Patterns Demonstrated | Execution Status |
|---|---|---|
| [`01_mart_county_scorecard_sf.sql`](01_mart_county_scorecard_sf.sql) | `QUALIFY`, `COUNT_IF`, `IFF`, multi-CTE county scorecard | Dialect-only (unexecuted) |
| [`02_mart_analyte_summary_sf.sql`](02_mart_analyte_summary_sf.sql) | `PERCENTILE_CONT`, `BOOLOR_AGG`, `COUNT_IF`, `IFF` | Dialect-only (unexecuted) |
| [`03_mart_system_screening_sf.sql`](03_mart_system_screening_sf.sql) | `IFF` analyte pivoting, `BOOLOR_AGG`, Hazard Index join | Dialect-only (unexecuted) |
| [`04_stage_copy_merge_load.sql`](04_stage_copy_merge_load.sql) | `FILE FORMAT`, internal `STAGE`, `COPY INTO` with `METADATA$FILENAME`, `VARIANT` (`OBJECT_CONSTRUCT`), `CLUSTER BY`, idempotent `MERGE` | Dialect-only (unexecuted) |

## Screening-Only Framing & Regulatory-Status Footnote

All queries implement informational occurrence screening of public-domain EPA UCMR 5 North Carolina data against all six 2024 EPA PFAS MCL and Hazard Index benchmarks ([89 FR 32532](https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation)) — never compliance determinations. EPA's rulemaking concerning potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards while retaining PFOA and PFOS is **proposed / not final** ([EPA Proposed PFAS Rescission Rule](https://www.epa.gov/sdwa/proposed-pfas-rescission-rule)).
