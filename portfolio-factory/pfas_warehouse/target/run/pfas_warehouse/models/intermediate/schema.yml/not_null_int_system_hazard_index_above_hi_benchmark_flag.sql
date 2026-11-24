
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select above_hi_benchmark_flag
from "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
where above_hi_benchmark_flag is null



  
  
      
    ) dbt_internal_test