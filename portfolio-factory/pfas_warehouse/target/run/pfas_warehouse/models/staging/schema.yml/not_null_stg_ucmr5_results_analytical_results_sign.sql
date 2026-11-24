
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select analytical_results_sign
from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
where analytical_results_sign is null



  
  
      
    ) dbt_internal_test