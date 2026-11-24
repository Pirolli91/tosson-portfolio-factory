
  
  create view "pfas_ucmr5"."main_staging"."stg_pws_county_crosswalk__dbt_tmp" as (
    -- Staging model: deduplicated NC PWSID-to-County crosswalk.
-- Any NC water system without an EPA SDWIS county match is explicitly labelled
-- 'UNMAPPED_COUNTY' so zero UCMR 5 occurrence records are ever dropped.

WITH distinct_systems AS (
    SELECT
        pwsid,
        MIN(pws_name) AS pws_name,
        MIN(size_code) AS size_code,
        MIN(size_category) AS size_category
    FROM "pfas_ucmr5"."main_staging"."stg_ucmr5_results"
    GROUP BY pwsid
),

sdwis AS (
    SELECT
        TRIM(pwsid) AS pwsid,
        TRIM(county_served) AS county_served,
        NULLIF(TRIM(city_served), '') AS city_served,
        NULLIF(TRIM(pws_type_code), '') AS pws_type_code
    FROM "pfas_ucmr5"."raw_ucmr5"."sdwis_nc_counties"
)

SELECT
    d.pwsid,
    d.pws_name,
    d.size_code,
    d.size_category,
    COALESCE(NULLIF(s.county_served, ''), 'UNMAPPED_COUNTY') AS county_name,
    s.city_served,
    COALESCE(s.pws_type_code, 'UNKNOWN') AS pws_type_code,
    (s.county_served IS NOT NULL AND TRIM(s.county_served) <> '') AS is_county_mapped
FROM distinct_systems d
LEFT JOIN sdwis s
    ON d.pwsid = s.pwsid
  );
