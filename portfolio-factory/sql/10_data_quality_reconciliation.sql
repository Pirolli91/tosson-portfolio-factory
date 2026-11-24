-- =============================================================================
-- FILE: 10_data_quality_reconciliation.sql
-- JD KEYWORDS EVIDENCED: Data Quality, Audit SQL, Orphan Key Checks, Row Reconciliation
-- PURPOSE: End-to-end warehouse reconciliation verifying exact row counts, zero
--          orphan keys, null-rate diagnostics, and county mapping coverage.
-- FRAMING: Informational UCMR 5 occurrence screening data quality audit.
-- =============================================================================

WITH audit AS (
    SELECT source_nc_rows, loaded_nc_rows, distinct_pwsids, mapped_pwsids, unmapped_pwsids
    FROM raw_ucmr5.ingest_audit
),
stg AS (
    SELECT
        COUNT(*) AS stg_rows,
        SUM(CASE WHEN pwsid IS NULL THEN 1 ELSE 0 END) AS null_pwsids,
        SUM(CASE WHEN collection_date IS NULL THEN 1 ELSE 0 END) AS null_dates,
        SUM(CASE WHEN is_detected AND result_ppt IS NULL THEN 1 ELSE 0 END) AS detected_missing_value
    FROM main_staging.stg_ucmr5_results
),
mart_c AS (
    SELECT COUNT(*) AS county_count, SUM(total_samples) AS county_sum_rows
    FROM main_marts.mart_county_scorecard
),
mart_s AS (
    SELECT COUNT(*) AS system_count, SUM(total_samples) AS system_sum_rows
    FROM main_marts.mart_system_screening
),
orphan_check AS (
    SELECT COUNT(*) AS orphan_pwsids
    FROM main_staging.stg_ucmr5_results r
    LEFT JOIN main_staging.stg_pws_county_crosswalk c
        ON r.pwsid = c.pwsid
    WHERE c.pwsid IS NULL
)
SELECT
    a.source_nc_rows,
    a.loaded_nc_rows,
    s.stg_rows,
    mc.county_sum_rows,
    ms.system_sum_rows,
    (
        a.source_nc_rows = a.loaded_nc_rows
        AND a.loaded_nc_rows = s.stg_rows
        AND s.stg_rows = mc.county_sum_rows
        AND s.stg_rows = ms.system_sum_rows
    ) AS all_layers_reconciled,
    a.distinct_pwsids,
    a.mapped_pwsids,
    a.unmapped_pwsids,
    mc.county_count,
    ms.system_count,
    o.orphan_pwsids,
    s.null_pwsids,
    s.null_dates,
    s.detected_missing_value
FROM audit a
CROSS JOIN stg s
CROSS JOIN mart_c mc
CROSS JOIN mart_s ms
CROSS JOIN orphan_check o;
