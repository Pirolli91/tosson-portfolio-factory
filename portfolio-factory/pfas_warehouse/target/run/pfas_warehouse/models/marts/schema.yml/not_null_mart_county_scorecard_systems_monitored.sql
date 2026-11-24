
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select systems_monitored
from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
where systems_monitored is null



  
  
      
    ) dbt_internal_test