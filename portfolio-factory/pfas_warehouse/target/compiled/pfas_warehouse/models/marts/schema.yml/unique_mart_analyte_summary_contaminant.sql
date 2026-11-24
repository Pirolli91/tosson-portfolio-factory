
    
    

select
    contaminant as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_marts"."mart_analyte_summary"
where contaminant is not null
group by contaminant
having count(*) > 1


