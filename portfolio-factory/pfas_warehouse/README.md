# `pfas_warehouse` — dbt-core + DuckDB Project (Build A2)

**Owner / Legal Entity:** Temitope Soneye — *Tosson Services LLC dba Tosson Environmental Analytics*  
**Stack:** `dbt-core==1.12.7`, `dbt-duckdb==1.11.1`, `duckdb==1.5.6`  
**Data Source:** 100% public-domain U.S. EPA UCMR 5 North Carolina occurrence data + EPA SDWIS NC county geography.

## Model Lineage

```text
raw_ucmr5.ucmr5_nc_results ──▶ stg_ucmr5_results ──┐
raw_ucmr5.sdwis_nc_counties ──▶ stg_pws_county_crosswalk ──┼──▶ int_ucmr5_pfas_screened ──▶ mart_system_screening ──▶ mart_county_scorecard
seeds/epa_2024_pfas_benchmarks ──▶ stg_pfas_benchmarks ──┘           │                         └──▶ mart_analyte_summary
                                                                     └──▶ int_system_hazard_index ──┘
```

## Exact Reproduction Commands

From the workspace root (`/home/antigravity`):

```bash
# 1. Ingest live public EPA UCMR 5 NC occurrence data + SDWIS county lookup into DuckDB
.venv/bin/python portfolio-factory/ingest/ingest_ucmr5.py

# 2. Seed benchmarks, build all staging/intermediate/mart models, and run all schema + singular tests
PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt build \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse

# 3. Generate static dbt documentation (manifest.json, catalog.json, index.html)
PFAS_DUCKDB_PATH=/home/antigravity/portfolio-factory/warehouse/pfas_ucmr5.duckdb \
  .venv/bin/dbt docs generate \
  --project-dir portfolio-factory/pfas_warehouse \
  --profiles-dir portfolio-factory/pfas_warehouse
```

Or directly from `portfolio-factory/pfas_warehouse/`:

```bash
../../.venv/bin/dbt build --profiles-dir .
../../.venv/bin/dbt docs generate --profiles-dir .
```

## Screening-Only Framing & Regulatory-Status Footnote

- **Screening-only framing:** EPA UCMR 5 data measures unregulated contaminant occurrence. Comparing occurrence concentrations against EPA's 2024 National Primary Drinking Water Regulation (NPDWR) benchmarks (`PFOA 4 ppt`, `PFOS 4 ppt`, `PFHxS 10 ppt`, `PFNA 10 ppt`, `HFPO-DA 10 ppt`, and the 4-PFAS Hazard Index `1.0` using HBWCs `HFPO-DA=10`, `PFNA=10`, `PFHxS=10`, `PFBS=2000 ppt`) is strictly an informational screening exercise and never a compliance determination.
- **Regulatory-status footnote (proposed / not final):** All six 2024 EPA PFAS MCL screening benchmarks from the April 26, 2024 final rule ([89 FR 32532](https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation)) are implemented here. Note that EPA has issued a **proposed / not final** rulemaking regarding potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards while retaining PFOA and PFOS ([EPA Proposed PFAS Rescission Rule](https://www.epa.gov/sdwa/proposed-pfas-rescission-rule)).
