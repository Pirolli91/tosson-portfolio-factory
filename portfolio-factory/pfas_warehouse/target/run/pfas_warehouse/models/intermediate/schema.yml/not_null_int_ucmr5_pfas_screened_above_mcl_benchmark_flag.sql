
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select above_mcl_benchmark_flag
from "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
where above_mcl_benchmark_flag is null



  
  
      
    ) dbt_internal_test