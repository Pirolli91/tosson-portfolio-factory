
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select result_row_id
from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
where result_row_id is null



  
  
      
    ) dbt_internal_test