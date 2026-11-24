-- =============================================================================
-- FILE: 04_stage_copy_merge_load.sql
-- STATUS: Snowflake-dialect SQL (dialect-only; not executed against a Snowflake account)
-- JD KEYWORDS EVIDENCED: Snowflake STAGE, FILE FORMAT, COPY INTO, VARIANT, MERGE, Clustering
-- FRAMING: EPA UCMR 5 occurrence/screening load pattern (public EPA dataset only).
-- OWNER: Tosson Services LLC dba Tosson Environmental Analytics
-- =============================================================================

CREATE DATABASE IF NOT EXISTS PFAS_ANALYTICS;
CREATE SCHEMA IF NOT EXISTS PFAS_ANALYTICS.RAW_UCMR5;
CREATE SCHEMA IF NOT EXISTS PFAS_ANALYTICS.INTERMEDIATE;
CREATE SCHEMA IF NOT EXISTS PFAS_ANALYTICS.MARTS;

-- 1. Tab-delimited EPA UCMR 5 file format + internal stage
CREATE OR REPLACE FILE FORMAT PFAS_ANALYTICS.RAW_UCMR5.FF_UCMR5_TSV
    TYPE = 'CSV'
    FIELD_DELIMITER = '\t'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL')
    EMPTY_FIELD_AS_NULL = TRUE
    ENCODING = 'ISO-8859-1';

CREATE OR REPLACE STAGE PFAS_ANALYTICS.RAW_UCMR5.STG_EPA_UCMR5_INTERNAL
    FILE_FORMAT = PFAS_ANALYTICS.RAW_UCMR5.FF_UCMR5_TSV
    COMMENT = 'Internal Snowflake stage for public EPA UCMR 5 NC occurrence extracts (dialect-only spec)';

-- 2. Landing table with VARIANT ingest metadata column and clustering by state/collection_date
CREATE TABLE IF NOT EXISTS PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_RESULTS (
    pwsid VARCHAR(16) NOT NULL,
    pws_name VARCHAR(256),
    size_code VARCHAR(8),
    facility_id VARCHAR(32),
    sample_point_id VARCHAR(32),
    collection_date DATE,
    sample_id VARCHAR(64),
    contaminant VARCHAR(64) NOT NULL,
    mrl_ug_l DOUBLE,
    units VARCHAR(16),
    method_id VARCHAR(32),
    analytical_results_sign VARCHAR(4),
    analytical_result_value DOUBLE,
    state_code VARCHAR(4) NOT NULL,
    ingest_metadata VARIANT,
    loaded_at_utc TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (state_code, DATE_TRUNC('QUARTER', collection_date));

-- 3. Transient staging table populated via COPY INTO (filtered to State = 'NC')
CREATE OR REPLACE TRANSIENT TABLE PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_STAGE LIKE PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_RESULTS;

COPY INTO PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_STAGE (
    pwsid, pws_name, size_code, facility_id, sample_point_id,
    collection_date, sample_id, contaminant, mrl_ug_l, units,
    method_id, analytical_results_sign, analytical_result_value,
    state_code, ingest_metadata
)
FROM (
    SELECT
        $1::VARCHAR,
        $2::VARCHAR,
        $3::VARCHAR,
        $4::VARCHAR,
        $7::VARCHAR,
        COALESCE(TRY_TO_DATE($12, 'MM/DD/YYYY'), TRY_TO_DATE($12))::DATE,
        $13::VARCHAR,
        $14::VARCHAR,
        TRY_TO_DOUBLE($15),
        $16::VARCHAR,
        $17::VARCHAR,
        $18::VARCHAR,
        TRY_TO_DOUBLE($19),
        UPPER($23::VARCHAR),
        OBJECT_CONSTRUCT(
            'source_filename', METADATA$FILENAME,
            'file_row_number', METADATA$FILE_ROW_NUMBER,
            'source_url', 'https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule'
        )
    FROM @PFAS_ANALYTICS.RAW_UCMR5.STG_EPA_UCMR5_INTERNAL
    WHERE UPPER($23::VARCHAR) = 'NC'
)
ON_ERROR = 'ABORT_STATEMENT';

-- 4. Idempotent MERGE upsert into target raw table
MERGE INTO PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_RESULTS AS tgt
USING (
    SELECT *
    FROM PFAS_ANALYTICS.RAW_UCMR5.UCMR5_NC_STAGE
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY pwsid, sample_id, sample_point_id, collection_date, contaminant
        ORDER BY loaded_at_utc DESC
    ) = 1
) AS src
ON  tgt.pwsid = src.pwsid
AND tgt.sample_id = src.sample_id
AND tgt.sample_point_id = src.sample_point_id
AND tgt.collection_date = src.collection_date
AND tgt.contaminant = src.contaminant
WHEN MATCHED THEN UPDATE SET
    tgt.pws_name = src.pws_name,
    tgt.analytical_results_sign = src.analytical_results_sign,
    tgt.analytical_result_value = src.analytical_result_value,
    tgt.ingest_metadata = src.ingest_metadata,
    tgt.loaded_at_utc = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
    pwsid, pws_name, size_code, facility_id, sample_point_id,
    collection_date, sample_id, contaminant, mrl_ug_l, units,
    method_id, analytical_results_sign, analytical_result_value,
    state_code, ingest_metadata
) VALUES (
    src.pwsid, src.pws_name, src.size_code, src.facility_id, src.sample_point_id,
    src.collection_date, src.sample_id, src.contaminant, src.mrl_ug_l, src.units,
    src.method_id, src.analytical_results_sign, src.analytical_result_value,
    src.state_code, src.ingest_metadata
);
