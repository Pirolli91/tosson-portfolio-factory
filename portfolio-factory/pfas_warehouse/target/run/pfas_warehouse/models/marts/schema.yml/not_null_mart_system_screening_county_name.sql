
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select county_name
from "pfas_ucmr5"."main_marts"."mart_system_screening"
where county_name is null



  
  
      
    ) dbt_internal_test