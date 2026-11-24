-- Staging model: cleaned, typed EPA UCMR 5 North Carolina analytical results.
-- Framing: occurrence/screening data only (100% public-domain U.S. EPA dataset).

WITH src AS (
    SELECT * FROM "pfas_ucmr5"."raw_ucmr5"."ucmr5_nc_results"
),

typed AS (
    SELECT
        CAST(row_num AS BIGINT) AS result_row_id,
        TRIM(pwsid) AS pwsid,
        COALESCE(NULLIF(TRIM(pws_name), ''), 'UNKNOWN_SYSTEM') AS pws_name,
        UPPER(COALESCE(NULLIF(TRIM(size_code), ''), 'U')) AS size_code,
        CASE UPPER(COALESCE(NULLIF(TRIM(size_code), ''), 'U'))
            WHEN 'L' THEN 'Large (>10,000)'
            WHEN 'S' THEN 'Small (<=10,000)'
            ELSE 'Unknown'
        END AS size_category,
        NULLIF(TRIM(facility_id), '') AS facility_id,
        NULLIF(TRIM(facility_name), '') AS facility_name,
        NULLIF(TRIM(facility_water_type), '') AS facility_water_type,
        COALESCE(NULLIF(TRIM(sample_point_id), ''), 'UNKNOWN_SP') AS sample_point_id,
        NULLIF(TRIM(sample_point_name), '') AS sample_point_name,
        NULLIF(TRIM(sample_point_type), '') AS sample_point_type,
        COALESCE(
            CAST(TRY_STRPTIME(TRIM(collection_date_raw), '%m/%d/%Y') AS DATE),
            TRY_CAST(TRIM(collection_date_raw) AS DATE)
        ) AS collection_date,
        COALESCE(NULLIF(TRIM(sample_id), ''), 'UNKNOWN_SAMPLE') AS sample_id,
        TRIM(contaminant) AS contaminant,
        CASE
            WHEN LOWER(TRIM(contaminant)) = 'lithium' THEN 'Lithium'
            ELSE 'PFAS'
        END AS analyte_group,
        TRY_CAST(mrl_raw AS DOUBLE) AS mrl_ug_l,
        CASE
            WHEN TRY_CAST(mrl_raw AS DOUBLE) IS NOT NULL
            THEN TRY_CAST(mrl_raw AS DOUBLE) * 1000.0
            ELSE NULL
        END AS mrl_ppt,
        COALESCE(NULLIF(TRIM(units), ''), 'ug/L') AS units,
        NULLIF(TRIM(method_id), '') AS method_id,
        TRIM(analytical_results_sign) AS analytical_results_sign,
        (TRIM(analytical_results_sign) = '=') AS is_detected,
        CASE
            WHEN TRIM(analytical_results_sign) = '='
            THEN TRY_CAST(analytical_result_value_raw AS DOUBLE)
            ELSE NULL
        END AS result_ug_l,
        CASE
            WHEN TRIM(analytical_results_sign) = '='
                 AND TRY_CAST(analytical_result_value_raw AS DOUBLE) IS NOT NULL
            THEN TRY_CAST(analytical_result_value_raw AS DOUBLE) * 1000.0
            ELSE NULL
        END AS result_ppt,
        NULLIF(TRIM(sample_event_code), '') AS sample_event_code,
        NULLIF(TRIM(monitoring_requirement), '') AS monitoring_requirement,
        NULLIF(TRIM(epa_region), '') AS epa_region,
        UPPER(TRIM(state_code)) AS state_code
    FROM src
)

SELECT
    result_row_id,
    pwsid,
    pws_name,
    size_code,
    size_category,
    facility_id,
    facility_name,
    facility_water_type,
    sample_point_id,
    sample_point_name,
    sample_point_type,
    collection_date,
    EXTRACT(YEAR FROM collection_date)::INTEGER AS collection_year,
    EXTRACT(QUARTER FROM collection_date)::INTEGER AS collection_quarter,
    CAST(EXTRACT(YEAR FROM collection_date) AS VARCHAR)
        || '-Q'
        || CAST(EXTRACT(QUARTER FROM collection_date) AS VARCHAR) AS year_quarter,
    sample_id,
    contaminant,
    analyte_group,
    mrl_ug_l,
    mrl_ppt,
    units,
    method_id,
    analytical_results_sign,
    is_detected,
    result_ug_l,
    result_ppt,
    sample_event_code,
    monitoring_requirement,
    epa_region,
    state_code
FROM typed