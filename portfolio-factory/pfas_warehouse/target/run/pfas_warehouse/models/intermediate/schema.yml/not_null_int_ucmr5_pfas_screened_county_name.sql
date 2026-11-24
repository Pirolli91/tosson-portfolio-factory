
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select county_name
from "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
where county_name is null



  
  
      
    ) dbt_internal_test