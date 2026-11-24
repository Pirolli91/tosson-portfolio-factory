# PFAS UCMR 5 Pipeline Run Summary — 2025-10-01

- **Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Airflow DAG:** `pfas_ucmr5_pipeline` (`LocalExecutor` on SQLite WAL)
- **Logical Date (`ds`):** `2025-10-01`
- **Run Type:** `DagRunType.BACKFILL`
- **Published (UTC):** `2026-11-24T00:31:50Z`

## Warehouse Reconciliation & Quality Gates

| Check | Value | Status |
|---|---|---|
| EPA UCMR 5 NC Source Rows | `68,633` | Reconciled (`==` loaded) |
| DuckDB Loaded Rows (`raw_ucmr5.ucmr5_nc_results`) | `68,633` | `reconciled=True` |
| Source Archive SHA-256 | `313c88a247ab41c7...` | Verified |
| Distinct NC Water Systems (`PWSID`) | `291` (`291` mapped, `0` unmapped) | Complete |
| NC Counties Screened | `92` | Complete |
| Systems Above Any 2024 Screening Benchmark | `117` | Screening-only |
| dbt Data & Schema Tests Passed | `50` passed / `0` failed | **PASS** |

## Top 10 NC Counties by Samples Above 2024 EPA MCL Screening Benchmarks

| Rank | County | Systems | Total Samples | PFAS Detections | Above 2024 MCL Benchmark | Systems Above Benchmark | Max Ratio (x) | Primary Analyte |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Cumberland | 6 | 3,600 | 557 | 189 | 6 | 8.32x | PFOS |
| 2 | Johnston | 9 | 1,855 | 236 | 74 | 9 | 3.75x | PFOS |
| 3 | Wake | 7 | 7,280 | 332 | 57 | 4 | 15.26x | PFOA |
| 4 | Pitt | 8 | 2,350 | 130 | 46 | 8 | 2.88x | PFOS |
| 5 | Harnett | 5 | 695 | 156 | 46 | 5 | 3.60x | PFOS |
| 6 | Brunswick | 6 | 850 | 148 | 41 | 4 | 3.75x | PFOS |
| 7 | Guilford | 7 | 1,080 | 144 | 40 | 5 | 8.90x | PFOS |
| 8 | Alamance | 5 | 660 | 55 | 33 | 4 | 4.25x | PFOS |
| 9 | Nash | 3 | 635 | 38 | 32 | 3 | 122.50x | PFOS |
| 10 | Lenoir | 3 | 2,555 | 92 | 30 | 3 | 2.88x | PFOS |

---
**Screening-Only Framing:** EPA UCMR 5 measures unregulated contaminant occurrence. Comparisons against EPA's six 2024 PFAS drinking-water screening benchmarks (PFOA 4 ppt, PFOS 4 ppt, PFHxS 10 ppt, PFNA 10 ppt, HFPO-DA 10 ppt, Hazard Index 1.0) are informational screening only and never compliance determinations. EPA's rulemaking on potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards is **proposed / not final** (https://www.epa.gov/sdwa/proposed-pfas-rescission-rule; https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation).
