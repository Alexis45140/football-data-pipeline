{{ config(
    materialized='table') }}
SELECT
    joueur,
    club_depart,
    club_arrivee,
    montant,
    date_transfert,        
    type_transfert
FROM {{ ref('stg_football_transfers') }}