
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select county_name
from "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk"
where county_name is null



  
  
      
    ) dbt_internal_test