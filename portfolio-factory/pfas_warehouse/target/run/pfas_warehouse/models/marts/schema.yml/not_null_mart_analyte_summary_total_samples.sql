
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_samples
from "pfas_ucmr5"."main_marts"."mart_analyte_summary"
where total_samples is null



  
  
      
    ) dbt_internal_test