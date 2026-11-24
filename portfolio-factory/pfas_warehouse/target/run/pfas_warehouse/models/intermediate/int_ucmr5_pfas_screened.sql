
  
  create view "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened__dbt_tmp" as (
    -- Intermediate model: NC UCMR 5 analytical results joined to county crosswalk and
-- 2024 EPA PFAS MCL / HBWC screening benchmarks.
-- Screening-only framing: benchmark flags indicate occurrence vs 2024 EPA screening
-- benchmarks and never regulatory compliance determinations.

WITH results AS (
    SELECT * FROM "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
),

crosswalk AS (
    SELECT
        pwsid,
        county_name,
        city_served,
        pws_type_code,
        is_county_mapped
    FROM "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk"
),

benchmarks AS (
    SELECT * FROM "pfas_ucmr5"."main_staging"."stg_pfas_benchmarks"
)

SELECT
    r.result_row_id,
    r.pwsid,
    r.pws_name,
    c.county_name,
    c.city_served,
    c.pws_type_code,
    c.is_county_mapped,
    r.size_code,
    r.size_category,
    r.facility_id,
    r.facility_name,
    r.facility_water_type,
    r.sample_point_id,
    r.sample_point_name,
    r.sample_point_type,
    r.collection_date,
    r.collection_year,
    r.collection_quarter,
    r.year_quarter,
    r.sample_id,
    r.contaminant,
    r.analyte_group,
    r.mrl_ug_l,
    r.mrl_ppt,
    r.units,
    r.method_id,
    r.analytical_results_sign,
    r.is_detected,
    r.result_ug_l,
    r.result_ppt,
    r.sample_event_code,
    r.monitoring_requirement,
    r.state_code,
    b.mcl_benchmark_ppt,
    b.mcl_benchmark_ug_l,
    b.hbwc_ppt,
    b.hbwc_ug_l,
    COALESCE(b.in_hazard_index, FALSE) AS in_hazard_index,
    (b.mcl_benchmark_ppt IS NOT NULL) AS has_mcl_benchmark_flag,
    CASE
        WHEN r.is_detected
             AND b.mcl_benchmark_ppt IS NOT NULL
             AND b.mcl_benchmark_ppt > 0
             AND r.result_ppt IS NOT NULL
        THEN r.result_ppt / b.mcl_benchmark_ppt
        ELSE NULL
    END AS benchmark_ratio,
    CASE
        WHEN r.is_detected
             AND b.mcl_benchmark_ppt IS NOT NULL
             AND r.result_ppt IS NOT NULL
             AND r.result_ppt > b.mcl_benchmark_ppt
        THEN TRUE
        ELSE FALSE
    END AS above_mcl_benchmark_flag,
    CASE
        WHEN r.is_detected
             AND COALESCE(b.in_hazard_index, FALSE)
             AND b.hbwc_ppt IS NOT NULL
             AND b.hbwc_ppt > 0
             AND r.result_ppt IS NOT NULL
        THEN r.result_ppt / b.hbwc_ppt
        ELSE 0.0
    END AS hbwc_component_ratio
FROM results r
INNER JOIN crosswalk c
    ON r.pwsid = c.pwsid
LEFT JOIN benchmarks b
    ON r.contaminant = b.contaminant
  );
