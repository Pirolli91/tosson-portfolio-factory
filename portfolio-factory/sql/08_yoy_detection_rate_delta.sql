-- =============================================================================
-- FILE: 08_yoy_detection_rate_delta.sql
-- JD KEYWORDS EVIDENCED: YoY Analytics, Period-over-Period LAG, Zero-Division Guards (NULLIF)
-- PURPOSE: Measure year-over-year changes in NC PFAS detection rate and 2024 MCL
--          screening benchmark exceedance rate across UCMR 5 collection years.
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

WITH annual AS (
    SELECT
        collection_year,
        COUNT(*) AS pfas_samples,
        SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) AS pfas_detections,
        ROUND(100.0 * SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2)
            AS pfas_detection_rate_pct,
        SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS samples_above_mcl_benchmark,
        ROUND(
            100.0 * SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN has_mcl_benchmark_flag THEN 1 ELSE 0 END), 0),
            2
        ) AS mcl_exceedance_rate_pct
    FROM main_intermediate.int_ucmr5_pfas_screened
    WHERE analyte_group = 'PFAS'
    GROUP BY collection_year
)
SELECT
    collection_year,
    pfas_samples,
    pfas_detections,
    pfas_detection_rate_pct,
    LAG(pfas_detection_rate_pct) OVER (ORDER BY collection_year) AS prior_year_detection_rate_pct,
    ROUND(
        pfas_detection_rate_pct - LAG(pfas_detection_rate_pct) OVER (ORDER BY collection_year),
        2
    ) AS detection_rate_yoy_pp_delta,
    samples_above_mcl_benchmark,
    mcl_exceedance_rate_pct,
    ROUND(
        100.0 * (
            samples_above_mcl_benchmark
            - LAG(samples_above_mcl_benchmark) OVER (ORDER BY collection_year)
        ) / NULLIF(LAG(samples_above_mcl_benchmark) OVER (ORDER BY collection_year), 0),
        2
    ) AS samples_above_mcl_yoy_pct_change
FROM annual
ORDER BY collection_year;
