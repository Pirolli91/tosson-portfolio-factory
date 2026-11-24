
  
  create view "pfas_ucmr5"."main_staging"."stg_pfas_benchmarks__dbt_tmp" as (
    -- Staging model: 2024 EPA NPDWR PFAS MCL and Hazard Index HBWC screening benchmarks.
-- Regulatory-status note (proposed / not final): All six 2024 benchmarks are retained
-- for transparent occurrence screening; see README for primary EPA / Federal Register URLs.

SELECT
    TRIM(contaminant) AS contaminant,
    CAST(mcl_benchmark_ppt AS DOUBLE) AS mcl_benchmark_ppt,
    CAST(mcl_benchmark_ug_l AS DOUBLE) AS mcl_benchmark_ug_l,
    CAST(hbwc_ppt AS DOUBLE) AS hbwc_ppt,
    CAST(hbwc_ug_l AS DOUBLE) AS hbwc_ug_l,
    CAST(in_hazard_index AS BOOLEAN) AS in_hazard_index,
    TRIM(benchmark_type) AS benchmark_type,
    TRIM(regulatory_source_url) AS regulatory_source_url
FROM "pfas_ucmr5"."main_seeds"."epa_2024_pfas_benchmarks"
  );
