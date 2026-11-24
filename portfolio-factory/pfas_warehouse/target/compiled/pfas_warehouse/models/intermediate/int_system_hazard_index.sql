-- Intermediate model: per-(pwsid, sample_point_id, collection_date) EPA Hazard Index
-- screening score across HFPO-DA (10 ppt), PFNA (10 ppt), PFHxS (10 ppt), and PFBS (2000 ppt).
-- Takes MAX component ratio per analyte within a sampling point + date to avoid
-- double-counting split/duplicate lab aliquots before summing across the 4 mixture analytes.

WITH hi_analytes AS (
    SELECT
        pwsid,
        county_name,
        sample_point_id,
        collection_date,
        collection_year,
        year_quarter,
        contaminant,
        MAX(CASE WHEN is_detected THEN 1 ELSE 0 END) AS analyte_detected_flag,
        MAX(COALESCE(result_ppt, 0.0)) AS max_analyte_ppt,
        MAX(hbwc_component_ratio) AS analyte_hi_ratio
    FROM "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
    WHERE in_hazard_index = TRUE
    GROUP BY
        pwsid,
        county_name,
        sample_point_id,
        collection_date,
        collection_year,
        year_quarter,
        contaminant
),

aggregated AS (
    SELECT
        pwsid,
        county_name,
        sample_point_id,
        collection_date,
        collection_year,
        year_quarter,
        COUNT(DISTINCT contaminant) AS hi_analytes_sampled,
        SUM(analyte_detected_flag) AS hi_analytes_detected,
        SUM(analyte_hi_ratio) AS hazard_index_score,
        MAX(CASE WHEN contaminant = 'HFPO-DA' THEN analyte_hi_ratio ELSE 0.0 END) AS hfpo_da_hi_component,
        MAX(CASE WHEN contaminant = 'PFNA' THEN analyte_hi_ratio ELSE 0.0 END) AS pfna_hi_component,
        MAX(CASE WHEN contaminant = 'PFHxS' THEN analyte_hi_ratio ELSE 0.0 END) AS pfhxs_hi_component,
        MAX(CASE WHEN contaminant = 'PFBS' THEN analyte_hi_ratio ELSE 0.0 END) AS pfbs_hi_component
    FROM hi_analytes
    GROUP BY
        pwsid,
        county_name,
        sample_point_id,
        collection_date,
        collection_year,
        year_quarter
)

SELECT
    pwsid || '|' || sample_point_id || '|' || CAST(collection_date AS VARCHAR) AS hi_event_key,
    pwsid,
    county_name,
    sample_point_id,
    collection_date,
    collection_year,
    year_quarter,
    hi_analytes_sampled,
    hi_analytes_detected,
    ROUND(hazard_index_score, 6) AS hazard_index_score,
    ROUND(hfpo_da_hi_component, 6) AS hfpo_da_hi_component,
    ROUND(pfna_hi_component, 6) AS pfna_hi_component,
    ROUND(pfhxs_hi_component, 6) AS pfhxs_hi_component,
    ROUND(pfbs_hi_component, 6) AS pfbs_hi_component,
    (hazard_index_score > 1.0) AS above_hi_benchmark_flag
FROM aggregated