
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select is_detected
from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
where is_detected is null



  
  
      
    ) dbt_internal_test