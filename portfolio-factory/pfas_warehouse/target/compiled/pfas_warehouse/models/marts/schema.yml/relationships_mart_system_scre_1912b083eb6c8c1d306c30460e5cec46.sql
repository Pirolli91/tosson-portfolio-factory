
    
    

with child as (
    select county_name as from_field
    from "pfas_ucmr5"."main_marts"."mart_system_screening"
    where county_name is not null
),

parent as (
    select county_name as to_field
    from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


