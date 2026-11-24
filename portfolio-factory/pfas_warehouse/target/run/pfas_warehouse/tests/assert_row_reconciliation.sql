
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  -- Singular data test: exact row reconciliation across ingest_audit, staging, intermediate, and marts.
WITH audit AS (
    SELECT source_nc_rows, loaded_nc_rows, distinct_pwsids
    FROM "pfas_ucmr5"."raw_ucmr5"."ingest_audit"
),
stg_cnt AS (
    SELECT COUNT(*) AS n, COUNT(DISTINCT pwsid) AS pws_n FROM "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
),
int_cnt AS (
    SELECT COUNT(*) AS n FROM "pfas_ucmr5"."main_intermediate"."int_ucmr5_pfas_screened"
),
county_sum AS (
    SELECT SUM(total_samples) AS n, SUM(systems_monitored) AS pws_n FROM "pfas_ucmr5"."main_marts"."mart_county_scorecard"
),
analyte_sum AS (
    SELECT SUM(total_samples) AS n FROM "pfas_ucmr5"."main_marts"."mart_analyte_summary"
),
sys_cnt AS (
    SELECT COUNT(*) AS pws_n, SUM(total_samples) AS n FROM "pfas_ucmr5"."main_marts"."mart_system_screening"
)
SELECT
    a.source_nc_rows,
    a.loaded_nc_rows,
    s.n AS stg_rows,
    i.n AS int_rows,
    c.n AS county_mart_rows,
    an.n AS analyte_mart_rows,
    sy.n AS system_mart_rows,
    a.distinct_pwsids,
    s.pws_n AS stg_pwsids,
    c.pws_n AS county_pwsids,
    sy.pws_n AS system_pwsids
FROM audit a
CROSS JOIN stg_cnt s
CROSS JOIN int_cnt i
CROSS JOIN county_sum c
CROSS JOIN analyte_sum an
CROSS JOIN sys_cnt sy
WHERE a.source_nc_rows <> a.loaded_nc_rows
   OR a.loaded_nc_rows <> s.n
   OR s.n <> i.n
   OR s.n <> c.n
   OR s.n <> an.n
   OR s.n <> sy.n
   OR a.distinct_pwsids <> s.pws_n
   OR s.pws_n <> c.pws_n
   OR s.pws_n <> sy.pws_n
  
  
      
    ) dbt_internal_test