
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select in_hazard_index
from "pfas_ucmr5"."main_staging"."stg_pfas_benchmarks"
where in_hazard_index is null



  
  
      
    ) dbt_internal_test