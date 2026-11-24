
    

    create  table
      "pfas_ucmr5"."main_marts"."mart_system_screening__dbt_tmp"
  
    
    as (
      -- Mart model: NC Water System-level PFAS screening scorecard vs 2024 EPA benchmarks.
-- Screening-only language enforced across all columns and status labels.

WITH screened AS (
    SELECT * FROM "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
),

hi_by_system AS (
    SELECT
        pwsid,
        MAX(hazard_index_score) AS max_hazard_index_score,
        BOOL_OR(above_hi_benchmark_flag) AS above_hi_benchmark_flag,
        SUM(CASE WHEN above_hi_benchmark_flag THEN 1 ELSE 0 END) AS events_above_hi_benchmark
    FROM "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
    GROUP BY pwsid
),

system_agg AS (
    SELECT
        pwsid,
        MIN(pws_name) AS pws_name,
        MIN(county_name) AS county_name,
        MIN(size_code) AS size_code,
        MIN(size_category) AS size_category,
        MIN(collection_date) AS first_collection_date,
        MAX(collection_date) AS last_collection_date,
        COUNT(*) AS total_samples,
        SUM(CASE WHEN analyte_group = 'PFAS' THEN 1 ELSE 0 END) AS pfas_samples,
        SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) AS detected_samples,
        SUM(CASE WHEN analyte_group = 'PFAS' AND is_detected THEN 1 ELSE 0 END) AS pfas_detected_samples,
        SUM(CASE WHEN has_mcl_benchmark_flag THEN 1 ELSE 0 END) AS mcl_screened_samples,
        SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS samples_above_mcl_benchmark,
        MAX(CASE WHEN contaminant = 'PFOA' AND is_detected THEN result_ppt END) AS max_pfoa_ppt,
        MAX(CASE WHEN contaminant = 'PFOS' AND is_detected THEN result_ppt END) AS max_pfos_ppt,
        MAX(CASE WHEN contaminant = 'PFHxS' AND is_detected THEN result_ppt END) AS max_pfhxs_ppt,
        MAX(CASE WHEN contaminant = 'PFNA' AND is_detected THEN result_ppt END) AS max_pfna_ppt,
        MAX(CASE WHEN contaminant = 'HFPO-DA' AND is_detected THEN result_ppt END) AS max_hfpo_da_ppt,
        MAX(CASE WHEN contaminant = 'PFBS' AND is_detected THEN result_ppt END) AS max_pfbs_ppt,
        AVG(CASE WHEN analyte_group = 'PFAS' AND is_detected THEN result_ppt END) AS mean_detected_pfas_ppt,
        MAX(CASE WHEN analyte_group = 'PFAS' AND is_detected THEN result_ppt END) AS max_detected_pfas_ppt,
        MAX(benchmark_ratio) AS max_benchmark_ratio
    FROM screened
    GROUP BY pwsid
)

SELECT
    s.pwsid,
    s.pws_name,
    s.county_name,
    s.size_code,
    s.size_category,
    s.first_collection_date,
    s.last_collection_date,
    s.total_samples,
    s.pfas_samples,
    s.detected_samples,
    s.pfas_detected_samples,
    ROUND(100.0 * s.detected_samples / NULLIF(s.total_samples, 0), 2) AS detection_rate_pct,
    ROUND(100.0 * s.pfas_detected_samples / NULLIF(s.pfas_samples, 0), 2) AS pfas_detection_rate_pct,
    s.mcl_screened_samples,
    s.samples_above_mcl_benchmark,
    (s.samples_above_mcl_benchmark > 0) AS above_any_mcl_benchmark_flag,
    ROUND(s.max_pfoa_ppt, 3) AS max_pfoa_ppt,
    ROUND(s.max_pfos_ppt, 3) AS max_pfos_ppt,
    ROUND(s.max_pfhxs_ppt, 3) AS max_pfhxs_ppt,
    ROUND(s.max_pfna_ppt, 3) AS max_pfna_ppt,
    ROUND(s.max_hfpo_da_ppt, 3) AS max_hfpo_da_ppt,
    ROUND(s.max_pfbs_ppt, 3) AS max_pfbs_ppt,
    ROUND(s.mean_detected_pfas_ppt, 3) AS mean_detected_pfas_ppt,
    ROUND(s.max_detected_pfas_ppt, 3) AS max_detected_pfas_ppt,
    ROUND(s.max_benchmark_ratio, 3) AS max_benchmark_ratio,
    ROUND(COALESCE(h.max_hazard_index_score, 0.0), 4) AS max_hazard_index_score,
    COALESCE(h.above_hi_benchmark_flag, FALSE) AS above_hi_benchmark_flag,
    COALESCE(h.events_above_hi_benchmark, 0) AS events_above_hi_benchmark,
    CASE
        WHEN s.samples_above_mcl_benchmark > 0 AND COALESCE(h.above_hi_benchmark_flag, FALSE)
            THEN 'Above Individual MCL & Hazard Index Screening Benchmarks'
        WHEN s.samples_above_mcl_benchmark > 0
            THEN 'Above 2024 Individual MCL Screening Benchmark'
        WHEN COALESCE(h.above_hi_benchmark_flag, FALSE)
            THEN 'Above 2024 Hazard Index Screening Benchmark (>1.0)'
        WHEN s.pfas_detected_samples > 0
            THEN 'PFAS Detected Below 2024 Screening Benchmarks'
        WHEN s.detected_samples > 0
            THEN 'Non-PFAS Analyte Detected Only'
        ELSE 'No Detections (>= MRL)'
    END AS screening_status
FROM system_agg s
LEFT JOIN hi_by_system h
    ON s.pwsid = h.pwsid
ORDER BY
    s.samples_above_mcl_benchmark DESC,
    s.max_benchmark_ratio DESC NULLS LAST,
    s.pwsid ASC
    );
    
  