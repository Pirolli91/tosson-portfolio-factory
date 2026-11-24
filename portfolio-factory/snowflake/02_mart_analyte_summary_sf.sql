-- =============================================================================
-- FILE: 02_mart_analyte_summary_sf.sql
-- STATUS: Snowflake-dialect SQL (dialect-only; not executed against a Snowflake account)
-- JD KEYWORDS EVIDENCED: Snowflake SQL, PERCENTILE_CONT, COUNT_IF, IFF, BOOLOR_AGG
-- FRAMING: EPA UCMR 5 occurrence/screening vs 2024 EPA MCL benchmarks only.
-- OWNER: Tosson Services LLC dba Tosson Environmental Analytics
-- =============================================================================

CREATE OR REPLACE TABLE PFAS_ANALYTICS.MARTS.MART_ANALYTE_SUMMARY AS
WITH screened AS (
    SELECT * FROM PFAS_ANALYTICS.INTERMEDIATE.INT_UCMR5_PFAS_SCREENED
),
detected_percentiles AS (
    SELECT
        contaminant,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY result_ppt) AS p50_detected_ppt,
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY result_ppt) AS p90_detected_ppt
    FROM screened
    WHERE is_detected = TRUE
      AND result_ppt IS NOT NULL
    GROUP BY contaminant
)
SELECT
    s.contaminant,
    MIN(s.analyte_group) AS analyte_group,
    MAX(s.mcl_benchmark_ppt) AS mcl_benchmark_ppt,
    MAX(s.hbwc_ppt) AS hbwc_ppt,
    BOOLOR_AGG(s.in_hazard_index) AS in_hazard_index,
    COUNT(*) AS total_samples,
    COUNT(DISTINCT s.pwsid) AS systems_tested,
    COUNT(DISTINCT s.county_name) AS counties_tested,
    COUNT_IF(s.is_detected) AS detected_samples,
    ROUND(100.0 * COUNT_IF(s.is_detected) / NULLIF(COUNT(*), 0), 2) AS detection_rate_pct,
    ROUND(p.p50_detected_ppt, 3) AS p50_detected_ppt,
    ROUND(p.p90_detected_ppt, 3) AS p90_detected_ppt,
    ROUND(MAX(IFF(s.is_detected, s.result_ppt, NULL)), 3) AS max_detected_ppt,
    COUNT_IF(s.above_mcl_benchmark_flag) AS samples_above_mcl_benchmark,
    COUNT(DISTINCT IFF(s.above_mcl_benchmark_flag, s.pwsid, NULL)) AS systems_above_mcl_benchmark,
    ROUND(MAX(s.benchmark_ratio), 3) AS max_benchmark_ratio
FROM screened s
LEFT JOIN detected_percentiles p
    ON s.contaminant = p.contaminant
GROUP BY s.contaminant, p.p50_detected_ppt, p.p90_detected_ppt
ORDER BY
    samples_above_mcl_benchmark DESC,
    detected_samples DESC,
    s.contaminant ASC;
