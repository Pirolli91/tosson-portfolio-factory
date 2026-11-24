-- Singular data test: ensure no analytical concentration or MRL is negative.
SELECT
    result_row_id,
    pwsid,
    contaminant,
    result_ug_l,
    result_ppt,
    mrl_ug_l
FROM {{ ref('stg_ucmr5_results') }}
WHERE (result_ug_l IS NOT NULL AND result_ug_l < 0)
   OR (result_ppt IS NOT NULL AND result_ppt < 0)
   OR (mrl_ug_l IS NOT NULL AND mrl_ug_l < 0)
