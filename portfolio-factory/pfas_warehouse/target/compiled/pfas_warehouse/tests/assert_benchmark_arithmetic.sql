-- Singular data test: verify ug/L -> ppt conversion (x1000) and benchmark_ratio arithmetic within 1e-6.
SELECT
    result_row_id,
    pwsid,
    contaminant,
    result_ug_l,
    result_ppt,
    mcl_benchmark_ppt,
    benchmark_ratio,
    above_mcl_benchmark_flag
FROM "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
WHERE (
        result_ug_l IS NOT NULL
        AND ABS(result_ppt - (result_ug_l * 1000.0)) > 1e-6
      )
   OR (
        is_detected = TRUE
        AND mcl_benchmark_ppt IS NOT NULL
        AND result_ppt IS NOT NULL
        AND ABS(benchmark_ratio - (result_ppt / mcl_benchmark_ppt)) > 1e-6
      )
   OR (
        above_mcl_benchmark_flag = TRUE
        AND (mcl_benchmark_ppt IS NULL OR result_ppt IS NULL OR result_ppt <= mcl_benchmark_ppt)
      )
   OR (
        above_mcl_benchmark_flag = FALSE
        AND is_detected = TRUE
        AND mcl_benchmark_ppt IS NOT NULL
        AND result_ppt IS NOT NULL
        AND result_ppt > mcl_benchmark_ppt
      )