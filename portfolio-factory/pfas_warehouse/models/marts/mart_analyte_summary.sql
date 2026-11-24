-- Mart model: Per-analyte UCMR 5 occurrence and 2024 MCL screening summary (29 PFAS + lithium).

WITH screened AS (
    SELECT * FROM {{ ref('int_ucmr5_pfas_screened') }}
)

SELECT
    contaminant,
    MIN(analyte_group) AS analyte_group,
    MAX(mcl_benchmark_ppt) AS mcl_benchmark_ppt,
    MAX(hbwc_ppt) AS hbwc_ppt,
    BOOL_OR(in_hazard_index) AS in_hazard_index,
    COUNT(*) AS total_samples,
    COUNT(DISTINCT pwsid) AS systems_tested,
    COUNT(DISTINCT county_name) AS counties_tested,
    SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) AS detected_samples,
    ROUND(100.0 * SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2)
        AS detection_rate_pct,
    ROUND(
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY result_ppt)
            FILTER (WHERE is_detected AND result_ppt IS NOT NULL),
        3
    ) AS p50_detected_ppt,
    ROUND(
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY result_ppt)
            FILTER (WHERE is_detected AND result_ppt IS NOT NULL),
        3
    ) AS p90_detected_ppt,
    ROUND(MAX(CASE WHEN is_detected THEN result_ppt END), 3) AS max_detected_ppt,
    SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS samples_above_mcl_benchmark,
    COUNT(DISTINCT CASE WHEN above_mcl_benchmark_flag THEN pwsid END) AS systems_above_mcl_benchmark,
    ROUND(MAX(benchmark_ratio), 3) AS max_benchmark_ratio
FROM screened
GROUP BY contaminant
ORDER BY
    samples_above_mcl_benchmark DESC,
    detected_samples DESC,
    contaminant ASC
