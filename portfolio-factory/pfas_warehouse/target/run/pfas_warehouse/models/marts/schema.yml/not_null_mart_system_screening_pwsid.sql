
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select pwsid
from "pfas_ucmr5"."main_marts"."mart_system_screening"
where pwsid is null



  
  
      
    ) dbt_internal_test