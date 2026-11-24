
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        analyte_group as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
    group by analyte_group

)

select *
from all_values
where value_field not in (
    'PFAS','Lithium'
)



  
  
      
    ) dbt_internal_test