
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select hazard_index_score
from "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
where hazard_index_score is null



  
  
      
    ) dbt_internal_test