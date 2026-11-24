
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    hi_event_key as unique_field,
    count(*) as n_records

from "pfas_ucmr5"."main_intermediate"."int_system_hazard_index"
where hi_event_key is not null
group by hi_event_key
having count(*) > 1



  
  
      
    ) dbt_internal_test