
    
    

select
    pwsid as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_marts"."mart_system_screening"
where pwsid is not null
group by pwsid
having count(*) > 1


