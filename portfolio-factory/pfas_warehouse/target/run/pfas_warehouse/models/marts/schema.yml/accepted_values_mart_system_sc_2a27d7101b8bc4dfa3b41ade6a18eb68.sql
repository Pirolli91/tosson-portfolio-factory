
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        screening_status as value_field,
        count(*) as n_records

    from "pfas_ucmr5"."main_marts"."mart_system_screening"
    group by screening_status

)

select *
from all_values
where value_field not in (
    'Above Individual MCL & Hazard Index Screening Benchmarks','Above 2024 Individual MCL Screening Benchmark','Above 2024 Hazard Index Screening Benchmark (>1.0)','PFAS Detected Below 2024 Screening Benchmarks','Non-PFAS Analyte Detected Only','No Detections (>= MRL)'
)



  
  
      
    ) dbt_internal_test