-- =============================================================================
-- FILE: 02_sampling_gaps_and_islands.sql
-- JD KEYWORDS EVIDENCED: Gaps-and-Islands, LAG, LEAD, ROW_NUMBER, Consecutive Streaks
-- PURPOSE: Identify consecutive quarterly monitoring islands (streaks) per NC water
--          system and measure quarter-to-quarter gaps between UCMR 5 sampling events.
-- FRAMING: Informational UCMR 5 occurrence screening only.
-- =============================================================================

WITH system_quarters AS (
    SELECT DISTINCT
        pwsid,
        pws_name,
        county_name,
        collection_year,
        collection_quarter,
        (collection_year * 4 + collection_quarter) AS quarter_seq
    FROM main_intermediate.int_ucmr5_pfas_screened
),
sequenced AS (
    SELECT
        *,
        LAG(quarter_seq) OVER (PARTITION BY pwsid ORDER BY quarter_seq) AS prev_quarter_seq,
        LEAD(quarter_seq) OVER (PARTITION BY pwsid ORDER BY quarter_seq) AS next_quarter_seq,
        quarter_seq - ROW_NUMBER() OVER (PARTITION BY pwsid ORDER BY quarter_seq) AS island_key
    FROM system_quarters
),
islands AS (
    SELECT
        pwsid,
        MIN(pws_name) AS pws_name,
        MIN(county_name) AS county_name,
        island_key,
        COUNT(*) AS consecutive_quarters,
        MIN(CAST(collection_year AS VARCHAR) || '-Q' || CAST(collection_quarter AS VARCHAR)) AS island_start_quarter,
        MAX(CAST(collection_year AS VARCHAR) || '-Q' || CAST(collection_quarter AS VARCHAR)) AS island_end_quarter,
        MAX(COALESCE(quarter_seq - prev_quarter_seq - 1, 0)) AS max_prior_gap_quarters
    FROM sequenced
    GROUP BY pwsid, island_key
)
SELECT
    pwsid,
    pws_name,
    county_name,
    island_start_quarter,
    island_end_quarter,
    consecutive_quarters,
    max_prior_gap_quarters
FROM islands
ORDER BY consecutive_quarters DESC, pwsid ASC, island_start_quarter ASC
LIMIT 50;
