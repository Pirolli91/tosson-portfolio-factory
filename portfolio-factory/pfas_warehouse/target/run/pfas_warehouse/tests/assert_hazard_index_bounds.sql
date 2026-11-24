
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  -- Singular data test: verify Hazard Index score is non-negative, matches component sum,
-- and aligns with above_hi_benchmark_flag (> 1.0).
SELECT
    hi_event_key,
    hazard_index_score,
    hfpo_da_hi_component,
    pfna_hi_component,
    pfhxs_hi_component,
    pfbs_hi_component,
    above_hi_benchmark_flag
FROM "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
WHERE hazard_index_score < 0
   OR ABS(
        hazard_index_score - (
            hfpo_da_hi_component
            + pfna_hi_component
            + pfhxs_hi_component
            + pfbs_hi_component
        )
      ) > 1e-4
   OR (above_hi_benchmark_flag = TRUE AND hazard_index_score <= 1.0)
   OR (above_hi_benchmark_flag = FALSE AND hazard_index_score > 1.0)
  
  
      
    ) dbt_internal_test