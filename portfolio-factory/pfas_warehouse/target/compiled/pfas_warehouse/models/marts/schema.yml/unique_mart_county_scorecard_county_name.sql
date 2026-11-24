
    
    

select
    county_name as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
where county_name is not null
group by county_name
having count(*) > 1


