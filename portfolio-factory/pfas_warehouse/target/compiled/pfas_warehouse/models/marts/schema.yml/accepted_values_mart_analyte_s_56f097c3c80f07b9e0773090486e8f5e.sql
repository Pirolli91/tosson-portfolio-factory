
    
    

with all_values as (

    select
        analyte_group as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_marts"."mart_analyte_summary"
    group by analyte_group

)

select *
from all_values
where value_field not in (
    'PFAS','Lithium'
)


