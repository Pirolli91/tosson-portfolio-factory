
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select contaminant
from "pfas_ucmr5"."main_marts"."mart_analyte_summary"
where contaminant is null



  
  
      
    ) dbt_internal_test