
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select screening_status
from "pfas_ucmr5"."main_marts"."mart_system_screening"
where screening_status is null



  
  
      
    ) dbt_internal_test