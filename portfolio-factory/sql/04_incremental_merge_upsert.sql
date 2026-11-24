-- =============================================================================
-- FILE: 04_incremental_merge_upsert.sql
-- JD KEYWORDS EVIDENCED: Incremental MERGE, Upsert, Idempotent Warehouse Loads (DuckDB 1.5+)
-- PURPOSE: Demonstrate an idempotent MERGE INTO incremental update pattern against
--          a county screening snapshot table (executed on a scratch DB copy by runner).
-- FRAMING: Informational UCMR 5 occurrence screening vs 2024 EPA benchmarks only.
-- =============================================================================

CREATE TABLE IF NOT EXISTS main_marts.county_screening_snapshot_demo AS
SELECT
    county_name,
    systems_monitored,
    total_samples,
    samples_above_mcl_benchmark,
    primary_exceeding_analyte,
    CAST('2026-10-01' AS DATE) AS snapshot_as_of_date
FROM main_marts.mart_county_scorecard
WHERE samples_above_mcl_benchmark > 0;

MERGE INTO main_marts.county_screening_snapshot_demo AS tgt
USING (
    SELECT
        county_name,
        systems_monitored,
        total_samples,
        samples_above_mcl_benchmark,
        primary_exceeding_analyte,
        CAST('2026-11-01' AS DATE) AS snapshot_as_of_date
    FROM main_marts.mart_county_scorecard
) AS src
ON tgt.county_name = src.county_name
WHEN MATCHED AND (
    tgt.total_samples <> src.total_samples
    OR tgt.samples_above_mcl_benchmark <> src.samples_above_mcl_benchmark
    OR tgt.snapshot_as_of_date < src.snapshot_as_of_date
) THEN UPDATE SET
    systems_monitored = src.systems_monitored,
    total_samples = src.total_samples,
    samples_above_mcl_benchmark = src.samples_above_mcl_benchmark,
    primary_exceeding_analyte = src.primary_exceeding_analyte,
    snapshot_as_of_date = src.snapshot_as_of_date
WHEN NOT MATCHED THEN INSERT (
    county_name,
    systems_monitored,
    total_samples,
    samples_above_mcl_benchmark,
    primary_exceeding_analyte,
    snapshot_as_of_date
) VALUES (
    src.county_name,
    src.systems_monitored,
    src.total_samples,
    src.samples_above_mcl_benchmark,
    src.primary_exceeding_analyte,
    src.snapshot_as_of_date
);

SELECT
    COUNT(*) AS total_snapshot_counties,
    SUM(CASE WHEN samples_above_mcl_benchmark > 0 THEN 1 ELSE 0 END) AS counties_with_exceedances,
    MAX(snapshot_as_of_date) AS latest_snapshot_date
FROM main_marts.county_screening_snapshot_demo;
