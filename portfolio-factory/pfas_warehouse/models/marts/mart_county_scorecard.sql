-- Mart model: North Carolina County-level PFAS Screening Scorecard.
-- Compares EPA UCMR 5 occurrence results against 2024 EPA MCL & Hazard Index benchmarks
-- strictly for informational occurrence screening.

WITH screened AS (
    SELECT * FROM {{ ref('int_ucmr5_pfas_screened') }}
),

systems AS (
    SELECT * FROM {{ ref('mart_system_screening') }}
),

county_sample_agg AS (
    SELECT
        county_name,
        COUNT(*) AS total_samples,
        SUM(CASE WHEN analyte_group = 'PFAS' THEN 1 ELSE 0 END) AS pfas_samples,
        SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) AS detected_samples,
        SUM(CASE WHEN analyte_group = 'PFAS' AND is_detected THEN 1 ELSE 0 END) AS pfas_detected_samples,
        SUM(CASE WHEN has_mcl_benchmark_flag THEN 1 ELSE 0 END) AS mcl_screened_samples,
        SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS samples_above_mcl_benchmark,
        MAX(benchmark_ratio) AS max_benchmark_ratio,
        MAX(CASE WHEN analyte_group = 'PFAS' AND is_detected THEN result_ppt END) AS max_detected_pfas_ppt
    FROM screened
    GROUP BY county_name
),

county_system_agg AS (
    SELECT
        county_name,
        COUNT(*) AS systems_monitored,
        SUM(CASE WHEN above_any_mcl_benchmark_flag THEN 1 ELSE 0 END) AS systems_above_mcl_benchmark,
        SUM(CASE WHEN above_hi_benchmark_flag THEN 1 ELSE 0 END) AS systems_above_hi_benchmark,
        SUM(CASE WHEN above_any_mcl_benchmark_flag OR above_hi_benchmark_flag THEN 1 ELSE 0 END)
            AS systems_above_any_2024_benchmark,
        MAX(max_hazard_index_score) AS max_hazard_index_score
    FROM systems
    GROUP BY county_name
),

primary_analyte AS (
    SELECT
        county_name,
        contaminant AS primary_exceeding_analyte,
        ROW_NUMBER() OVER (
            PARTITION BY county_name
            ORDER BY COUNT(*) DESC, MAX(benchmark_ratio) DESC, contaminant ASC
        ) AS rn
    FROM screened
    WHERE above_mcl_benchmark_flag = TRUE
    GROUP BY county_name, contaminant
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
    AND pa.rn = 1
ORDER BY
    c.samples_above_mcl_benchmark DESC,
    sy.systems_above_any_2024_benchmark DESC,
    c.pfas_detected_samples DESC,
    c.county_name ASC
