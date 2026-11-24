-- =============================================================================
-- FILE: 07_outlier_iqr_zscore_screening.sql
-- JD KEYWORDS EVIDENCED: Statistical SQL, PERCENTILE_CONT, IQR, Z-Score Outlier Detection
-- PURPOSE: Flag high-magnitude PFAS detections per analyte using Tukey 1.5*IQR
--          upper fences and standardized z-scores for analytical QA review.
-- FRAMING: Informational UCMR 5 occurrence screening only.
-- =============================================================================

WITH analyte_stats AS (
    SELECT
        contaminant,
        COUNT(*) AS n_detected,
        AVG(result_ppt) AS mean_ppt,
        STDDEV_SAMP(result_ppt) AS stddev_ppt,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY result_ppt) AS q1_ppt,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY result_ppt) AS q3_ppt
    FROM main_intermediate.int_ucmr5_pfas_screened
    WHERE analyte_group = 'PFAS'
      AND is_detected = TRUE
      AND result_ppt IS NOT NULL
    GROUP BY contaminant
    HAVING COUNT(*) >= 5
),
scored AS (
    SELECT
        r.pwsid,
        r.pws_name,
        r.county_name,
        r.collection_date,
        r.contaminant,
        ROUND(r.result_ppt, 3) AS result_ppt,
        ROUND(s.q3_ppt + 1.5 * (s.q3_ppt - s.q1_ppt), 3) AS tukey_upper_fence_ppt,
        ROUND((r.result_ppt - s.mean_ppt) / NULLIF(s.stddev_ppt, 0), 2) AS z_score
    FROM main_intermediate.int_ucmr5_pfas_screened r
    INNER JOIN analyte_stats s
        ON r.contaminant = s.contaminant
    WHERE r.analyte_group = 'PFAS'
      AND r.is_detected = TRUE
      AND r.result_ppt IS NOT NULL
)
SELECT
    pwsid,
    pws_name,
    county_name,
    collection_date,
    contaminant,
    result_ppt,
    tukey_upper_fence_ppt,
    z_score
FROM scored
WHERE result_ppt > tukey_upper_fence_ppt
   OR z_score >= 2.0
ORDER BY z_score DESC NULLS LAST, result_ppt DESC
LIMIT 30;
