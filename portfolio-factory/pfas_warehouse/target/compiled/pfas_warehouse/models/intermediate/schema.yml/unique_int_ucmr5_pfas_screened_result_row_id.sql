
    
    

select
    result_row_id as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
where result_row_id is not null
group by result_row_id
having count(*) > 1


