
    
    

select
    contaminant as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_staging"."stg_pfas_benchmarks"
where contaminant is not null
group by contaminant
having count(*) > 1


