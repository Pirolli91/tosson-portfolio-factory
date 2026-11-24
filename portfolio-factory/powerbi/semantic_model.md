# Power BI Semantic Model Specification — NC EPA UCMR 5 PFAS Screening Explorer

**Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics  
**Scope Statement:** Power BI capability in Sprint 5 is evidenced by this semantic-model specification, [`model_spec.json`](model_spec.json), and the DAX measure library in [`measures.dax`](measures.dax). Authoring a binary `.pbix` file requires Power BI Desktop on Windows and is explicitly **out of scope** for this Linux-built sprint.

---

## 1. Star-Schema Architecture

The semantic model consumes the verified DuckDB dbt marts and intermediate screening grain produced by [`pfas_warehouse/`](../pfas_warehouse/):

| Table | Role | Source dbt Model | Grain |
|---|---|---|---|
| `fact_ucmr5_screening` | Fact | `int_ucmr5_pfas_screened` | One row per analytical result (`pwsid`, `sample_id`, `sample_point_id`, `collection_date`, `contaminant`) |
| `dim_water_system` | Dimension | `mart_system_screening` | One row per NC Public Water System (`pwsid`) |
| `dim_county` | Dimension | `mart_county_scorecard` | One row per NC County (`county_name`, including `'UNMAPPED_COUNTY'` where SDWIS lacks a county row) |
| `dim_analyte_benchmark` | Dimension | `stg_pfas_benchmarks` + distinct UCMR 5 contaminants | One row per UCMR 5 analyte (`contaminant`) |
| `dim_date` | Dimension (Marked as Date Table) | Derived calendar spine (`2023-01-01` – `2026-12-31`) | One row per calendar date (`date_key`) |

### Relationships (All Single-Direction `1:*`, Active)

1. `dim_water_system[pwsid]` (`1`) -> `fact_ucmr5_screening[pwsid]` (`*`) — Single direction
2. `dim_county[county_name]` (`1`) -> `dim_water_system[county_name]` (`*`) — Single direction (snowflake hop avoids ambiguous many-to-many county filtering; alternatively denormalized `county_name` on `fact_ucmr5_screening` with inactive relationship for direct slicer performance)
3. `dim_analyte_benchmark[contaminant]` (`1`) -> `fact_ucmr5_screening[contaminant]` (`*`) — Single direction
4. `dim_date[date_key]` (`1`) -> `fact_ucmr5_screening[collection_date]` (`*`) — Single direction (enables `SAMEPERIODLASTYEAR` YoY DAX measures)

---

## 2. Formatting, Sort-By & Governance Rules

- **Units:** All screening concentrations and benchmarks are standardized to **parts per trillion (`ppt`, equivalent to `ng/L`)** alongside raw EPA `ug/L` (`result_ppt = result_ug_l * 1000`).
- **Sort-By Columns:** `dim_date[month_name]` sorted by `dim_date[month_number]`; `dim_date[year_quarter]` sorted by `dim_date[year_quarter_sort]`.
- **Measure Display Folders:** `01. Volume & Coverage`, `02. Screening & Detection Rates`, `03. Concentration & Benchmark Ratios (ppt / ng/L)`, `04. EPA Hazard Index Screening`, `05. Year-over-Year (YoY) Screening Deltas`, `06. County Rankings & Dynamic Screening Labels`.
- **Row-Level Security (RLS):** Not required — 100% public-domain U.S. EPA dataset.

---

## 3. Screening-Only Framing & Regulatory-Status Footnote

- **UCMR 5 Screening-Only Framing:** EPA UCMR 5 monitoring collects occurrence data for unregulated contaminants. Comparisons to the 2024 EPA National Primary Drinking Water Regulation (NPDWR) MCLs (`PFOA 4 ppt`, `PFOS 4 ppt`, `PFHxS 10 ppt`, `PFNA 10 ppt`, `HFPO-DA 10 ppt`) and the mixture Hazard Index (`1.0` across `HFPO-DA`, `PFNA`, `PFHxS`, `PFBS`) are **informational occurrence screening benchmarks only** and never constitute regulatory compliance determinations.
- **Regulatory-Status Footnote (Proposed / Not Final):** All six 2024 EPA NPDWR benchmarks are implemented per the April 26, 2024 final rule ([89 FR 32532](https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation)). Note that EPA has published a **proposed / not final** rulemaking regarding potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards while retaining PFOA and PFOS ([EPA Proposed PFAS Rescission Rule](https://www.epa.gov/sdwa/proposed-pfas-rescission-rule)). All six 2024 benchmarks remain reported here for transparent screening continuity.
