-- =============================================================================
-- FILE: 01_county_ranking_windows.sql
-- JD KEYWORDS EVIDENCED: Window Functions, RANK, DENSE_RANK, PERCENT_RANK, NTILE
-- PURPOSE: Rank NC counties by 2024 PFAS MCL screening benchmark exceedances and
--          compute percentile standing + quartile tiers across monitored counties.
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

SELECT
    county_name,
    systems_monitored,
    total_samples,
    pfas_detected_samples,
    samples_above_mcl_benchmark,
    systems_above_any_2024_benchmark,
    max_benchmark_ratio,
    RANK() OVER (
        ORDER BY samples_above_mcl_benchmark DESC, max_benchmark_ratio DESC NULLS LAST
    ) AS screening_rank,
    DENSE_RANK() OVER (
        ORDER BY systems_above_any_2024_benchmark DESC
    ) AS dense_system_rank,
    ROUND(
        PERCENT_RANK() OVER (ORDER BY samples_above_mcl_benchmark ASC),
        4
    ) AS exceedance_percent_rank,
    NTILE(4) OVER (
        ORDER BY pfas_detection_rate_pct DESC, county_name ASC
    ) AS detection_quartile
FROM main_marts.mart_county_scorecard
ORDER BY screening_rank ASC, county_name ASC;
