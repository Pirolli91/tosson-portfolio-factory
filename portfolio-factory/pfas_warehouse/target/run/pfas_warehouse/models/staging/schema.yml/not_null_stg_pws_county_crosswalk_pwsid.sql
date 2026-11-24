
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select pwsid
from "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk"
where pwsid is null



  
  
      
    ) dbt_internal_test