-- =============================================================================
-- FILE: 05_hazard_index_mixture_cohort.sql
-- JD KEYWORDS EVIDENCED: Multi-Analyte CTE, Cohort Screening, EPA Hazard Index Formula
-- PURPOSE: Identify NC water systems with multi-PFAS mixture detections and rank
--          sampling events by 2024 EPA Hazard Index (HFPO-DA/10 + PFNA/10 + PFHxS/10 + PFBS/2000).
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

WITH hi_ranked AS (
    SELECT
        h.pwsid,
        s.pws_name,
        h.county_name,
        h.sample_point_id,
        h.collection_date,
        h.hi_analytes_detected,
        h.hazard_index_score,
        h.hfpo_da_hi_component,
        h.pfna_hi_component,
        h.pfhxs_hi_component,
        h.pfbs_hi_component,
        h.above_hi_benchmark_flag,
        ROW_NUMBER() OVER (
            PARTITION BY h.pwsid
            ORDER BY h.hazard_index_score DESC, h.collection_date DESC
        ) AS rn_peak_event
    FROM main_intermediate.int_system_hazard_index h
    INNER JOIN main_marts.mart_system_screening s
        ON h.pwsid = s.pwsid
    WHERE h.hazard_index_score > 0
)
SELECT
    pwsid,
    pws_name,
    county_name,
    collection_date AS peak_hi_date,
    hi_analytes_detected,
    hazard_index_score AS peak_hazard_index_score,
    hfpo_da_hi_component,
    pfna_hi_component,
    pfhxs_hi_component,
    pfbs_hi_component,
    above_hi_benchmark_flag
FROM hi_ranked
WHERE rn_peak_event = 1
ORDER BY peak_hazard_index_score DESC, pwsid ASC
LIMIT 30;
