
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select hi_event_key
from "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
where hi_event_key is null



  
  
      
    ) dbt_internal_test