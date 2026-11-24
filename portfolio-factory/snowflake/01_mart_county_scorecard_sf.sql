-- =============================================================================
-- FILE: 01_mart_county_scorecard_sf.sql
-- STATUS: Snowflake-dialect SQL (dialect-only; not executed against a Snowflake account)
-- JD KEYWORDS EVIDENCED: Snowflake SQL, QUALIFY, IFF, Window Functions, CTEs, Data Modeling
-- FRAMING: EPA UCMR 5 occurrence/screening vs 2024 EPA MCL & Hazard Index benchmarks only.
-- OWNER: Tosson Services LLC dba Tosson Environmental Analytics
-- =============================================================================

CREATE OR REPLACE TABLE PFAS_ANALYTICS.MARTS.MART_COUNTY_SCORECARD AS
WITH screened AS (
    SELECT * FROM PFAS_ANALYTICS.INTERMEDIATE.INT_UCMR5_PFAS_SCREENED
),
systems AS (
    SELECT * FROM PFAS_ANALYTICS.MARTS.MART_SYSTEM_SCREENING
),
county_sample_agg AS (
    SELECT
        county_name,
        COUNT(*) AS total_samples,
        COUNT_IF(analyte_group = 'PFAS') AS pfas_samples,
        COUNT_IF(is_detected) AS detected_samples,
        COUNT_IF(analyte_group = 'PFAS' AND is_detected) AS pfas_detected_samples,
        COUNT_IF(has_mcl_benchmark_flag) AS mcl_screened_samples,
        COUNT_IF(above_mcl_benchmark_flag) AS samples_above_mcl_benchmark,
        MAX(benchmark_ratio) AS max_benchmark_ratio,
        MAX(IFF(analyte_group = 'PFAS' AND is_detected, result_ppt, NULL)) AS max_detected_pfas_ppt
    FROM screened
    GROUP BY county_name
),
county_system_agg AS (
    SELECT
        county_name,
        COUNT(*) AS systems_monitored,
        COUNT_IF(above_any_mcl_benchmark_flag) AS systems_above_mcl_benchmark,
        COUNT_IF(above_hi_benchmark_flag) AS systems_above_hi_benchmark,
        COUNT_IF(above_any_mcl_benchmark_flag OR above_hi_benchmark_flag) AS systems_above_any_2024_benchmark,
        MAX(max_hazard_index_score) AS max_hazard_index_score
    FROM systems
    GROUP BY county_name
),
primary_analyte AS (
    SELECT
        county_name,
        contaminant AS primary_exceeding_analyte
    FROM screened
    WHERE above_mcl_benchmark_flag = TRUE
    GROUP BY county_name, contaminant
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY county_name
        ORDER BY COUNT(*) DESC, MAX(benchmark_ratio) DESC, contaminant ASC
    ) = 1
)
SELECT
    c.county_name,
    sy.systems_monitored,
    c.total_samples,
    c.pfas_samples,
    c.detected_samples,
    c.pfas_detected_samples,
    ROUND(100.0 * c.detected_samples / NULLIF(c.total_samples, 0), 2) AS detection_rate_pct,
    ROUND(100.0 * c.pfas_detected_samples / NULLIF(c.pfas_samples, 0), 2) AS pfas_detection_rate_pct,
    c.mcl_screened_samples,
    c.samples_above_mcl_benchmark,
    ROUND(100.0 * c.samples_above_mcl_benchmark / NULLIF(c.mcl_screened_samples, 0), 2)
        AS mcl_benchmark_exceedance_rate_pct,
    sy.systems_above_mcl_benchmark,
    sy.systems_above_hi_benchmark,
    sy.systems_above_any_2024_benchmark,
    ROUND(100.0 * sy.systems_above_any_2024_benchmark / NULLIF(sy.systems_monitored, 0), 2)
        AS share_systems_above_benchmark_pct,
    ROUND(c.max_benchmark_ratio, 3) AS max_benchmark_ratio,
    ROUND(c.max_detected_pfas_ppt, 3) AS max_detected_pfas_ppt,
    ROUND(COALESCE(sy.max_hazard_index_score, 0.0), 4) AS max_hazard_index_score,
    COALESCE(pa.primary_exceeding_analyte, 'None') AS primary_exceeding_analyte,
    CASE
        WHEN sy.systems_above_any_2024_benchmark > 0 THEN 'Above 2024 Screening Benchmark Observed'
        WHEN c.pfas_detected_samples > 0 THEN 'PFAS Detected Below 2024 Screening Benchmarks'
        ELSE 'No PFAS Detections (>= MRL)'
    END AS screening_summary_label
FROM county_sample_agg c
INNER JOIN county_system_agg sy
    ON c.county_name = sy.county_name
LEFT JOIN primary_analyte pa
    ON c.county_name = pa.county_name
ORDER BY
    c.samples_above_mcl_benchmark DESC,
    sy.systems_above_any_2024_benchmark DESC,
    c.county_name ASC;
