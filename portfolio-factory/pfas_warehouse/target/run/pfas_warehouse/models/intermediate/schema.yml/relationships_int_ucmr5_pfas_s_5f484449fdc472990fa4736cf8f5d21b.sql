
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select pwsid as from_field
    from "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
    where pwsid is not null
),

parent as (
    select pwsid as to_field
    from "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test