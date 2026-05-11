{{ config(
    materialized='table'
) }}

WITH base AS (
    SELECT * FROM {{ ref('stg_football_transfers') }}
)

SELECT 
    *,
    -- On cherche la colonne qui contient '2026-05-10...' 
    -- Si elle s'appelle date_transfert, on la transforme ici :
    SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', date_transfert) AS transfer_timestamp_clean,
    SAFE.PARSE_DATE('%Y-%m-%d', LEFT(date_transfert, 10)) AS transfer_date_clean
FROM base