
    
    

with all_values as (

    select
        screening_summary_label as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_marts"."mart_county_scorecard"
    group by screening_summary_label

)

select *
from all_values
where value_field not in (
    'Above 2024 Screening Benchmark Observed','PFAS Detected Below 2024 Screening Benchmarks','No PFAS Detections (>= MRL)'
)


