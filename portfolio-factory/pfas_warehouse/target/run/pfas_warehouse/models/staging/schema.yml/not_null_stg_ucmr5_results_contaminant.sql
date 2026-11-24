
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select contaminant
from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
where contaminant is null



  
  
      
    ) dbt_internal_test