-- =============================================================================
-- FILE: 09_system_size_pareto_share.sql
-- JD KEYWORDS EVIDENCED: Cumulative Share, Pareto Analysis, SUM() OVER Running Totals
-- PURPOSE: Compute cumulative Pareto share of statewide 2024 MCL screening benchmark
--          exceedances across NC counties and system size tiers.
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

WITH ranked_counties AS (
    SELECT
        county_name,
        systems_monitored,
        samples_above_mcl_benchmark,
        SUM(samples_above_mcl_benchmark) OVER () AS statewide_above_mcl_samples,
        SUM(samples_above_mcl_benchmark) OVER (
            ORDER BY samples_above_mcl_benchmark DESC, county_name ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_above_mcl_samples,
        ROW_NUMBER() OVER (
            ORDER BY samples_above_mcl_benchmark DESC, county_name ASC
        ) AS county_pareto_rank
    FROM main_marts.mart_county_scorecard
    WHERE samples_above_mcl_benchmark > 0
)
SELECT
    county_pareto_rank,
    county_name,
    systems_monitored,
    samples_above_mcl_benchmark,
    ROUND(100.0 * samples_above_mcl_benchmark / NULLIF(statewide_above_mcl_samples, 0), 2)
        AS share_of_statewide_pct,
    cumulative_above_mcl_samples,
    ROUND(100.0 * cumulative_above_mcl_samples / NULLIF(statewide_above_mcl_samples, 0), 2)
        AS cumulative_pareto_pct
FROM ranked_counties
ORDER BY county_pareto_rank ASC;
