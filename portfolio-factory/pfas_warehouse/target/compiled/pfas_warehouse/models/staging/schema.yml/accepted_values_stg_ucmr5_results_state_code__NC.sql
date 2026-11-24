
    
    

with all_values as (

    select
        state_code as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
    group by state_code

)

select *
from all_values
where value_field not in (
    'NC'
)


