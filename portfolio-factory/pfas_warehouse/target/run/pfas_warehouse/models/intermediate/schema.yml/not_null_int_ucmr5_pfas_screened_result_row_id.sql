
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select result_row_id
from "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
where result_row_id is null



  
  
      
    ) dbt_internal_test