
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select screening_summary_label
from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
where screening_summary_label is null



  
  
      
    ) dbt_internal_test