-- =============================================================================
-- FILE: 06_analyte_pivot_conditional_agg.sql
-- JD KEYWORDS EVIDENCED: Conditional Aggregation, Pivoting, CASE WHEN Matrix
-- PURPOSE: Pivot county-level maximum detected concentrations (ppt) across all
--          six 2024 EPA PFAS benchmark analytes in a single analytical matrix.
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

SELECT
    county_name,
    COUNT(DISTINCT pwsid) AS systems_screened,
    ROUND(MAX(CASE WHEN contaminant = 'PFOA' AND is_detected THEN result_ppt END), 2) AS max_pfoa_ppt,
    ROUND(MAX(CASE WHEN contaminant = 'PFOS' AND is_detected THEN result_ppt END), 2) AS max_pfos_ppt,
    ROUND(MAX(CASE WHEN contaminant = 'PFHxS' AND is_detected THEN result_ppt END), 2) AS max_pfhxs_ppt,
    ROUND(MAX(CASE WHEN contaminant = 'PFNA' AND is_detected THEN result_ppt END), 2) AS max_pfna_ppt,
    ROUND(MAX(CASE WHEN contaminant = 'HFPO-DA' AND is_detected THEN result_ppt END), 2) AS max_hfpo_da_ppt,
    ROUND(MAX(CASE WHEN contaminant = 'PFBS' AND is_detected THEN result_ppt END), 2) AS max_pfbs_ppt,
    SUM(CASE WHEN above_mcl_benchmark_flag THEN 1 ELSE 0 END) AS total_samples_above_mcl
FROM main_intermediate.int_ucmr5_pfas_screened
WHERE contaminant IN ('PFOA', 'PFOS', 'PFHxS', 'PFNA', 'HFPO-DA', 'PFBS')
GROUP BY county_name
HAVING SUM(CASE WHEN is_detected THEN 1 ELSE 0 END) > 0
ORDER BY total_samples_above_mcl DESC, county_name ASC
LIMIT 30;
