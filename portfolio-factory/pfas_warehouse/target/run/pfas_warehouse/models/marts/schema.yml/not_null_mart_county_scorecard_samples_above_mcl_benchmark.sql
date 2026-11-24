
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select samples_above_mcl_benchmark
from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
where samples_above_mcl_benchmark is null



  
  
      
    ) dbt_internal_test