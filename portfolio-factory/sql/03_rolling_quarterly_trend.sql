-- =============================================================================
-- FILE: 03_rolling_quarterly_trend.sql
-- JD KEYWORDS EVIDENCED: Moving Averages, ROWS BETWEEN Window Frames, Time-Series SQL
-- PURPOSE: Track statewide quarterly PFAS detection rate and 3-quarter rolling
--          average of samples above 2024 EPA MCL screening benchmarks.
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

WITH quarterly AS (
    SELECT
        collection_year,
        collection_quarter,
        year_quarter,
        COUNT(*) AS pfas_samples,
        SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) AS pfas_detections,
        ROUND(100.0 * SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2)
            AS pfas_detection_rate_pct,
        SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS samples_above_mcl_benchmark
    FROM main_intermediate.int_ucmr5_pfas_screened
    WHERE analyte_group = 'PFAS'
    GROUP BY collection_year, collection_quarter, year_quarter
)
SELECT
    year_quarter,
    pfas_samples,
    pfas_detections,
    pfas_detection_rate_pct,
    ROUND(
        AVG(pfas_detection_rate_pct) OVER (
            ORDER BY collection_year, collection_quarter
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_3q_detection_rate_pct,
    samples_above_mcl_benchmark,
    SUM(samples_above_mcl_benchmark) OVER (
        ORDER BY collection_year, collection_quarter
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_above_benchmark_samples
FROM quarterly
ORDER BY collection_year, collection_quarter;
