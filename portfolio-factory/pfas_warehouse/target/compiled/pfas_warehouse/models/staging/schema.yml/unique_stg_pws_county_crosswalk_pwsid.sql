
    
    

select
    pwsid as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk"
where pwsid is not null
group by pwsid
having count(*) > 1


