{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ ref('transferts_football') }}
),

renamed AS (
    SELECT
        joueur,
        club_depart,
        club_arrivee,
        CAST(montant AS FLOAT64) AS montant,
        PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', date_transfert) AS date_transfert,
        type_transfert
    FROM source
)

SELECT * FROM renamed