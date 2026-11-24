
    
    

with all_values as (

    select
        analytical_results_sign as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
    group by analytical_results_sign

)

select *
from all_values
where value_field not in (
    '<','='
)


