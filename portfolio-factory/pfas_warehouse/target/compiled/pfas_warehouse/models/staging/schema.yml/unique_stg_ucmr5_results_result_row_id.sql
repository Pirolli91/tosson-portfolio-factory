
    
    

select
    result_row_id as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
where result_row_id is not null
group by result_row_id
having count(*) > 1


