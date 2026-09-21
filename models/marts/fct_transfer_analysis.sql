{{ config(
    materialized='table',
    partition_by={'field': 'date_transfert', 'data_type': 'timestamp', 'granularity': 'month'},
    cluster_by=['type_transfert']
) }}

-- Reconstruction complete a chaque run. Le sandbox BigQuery interdit le DML,
-- donc pas de merge incremental : l'accumulation se fait en amont, dans
-- transfers_raw que l'extraction alimente en append et que le staging
-- dedoublonne. Le CTAS relit donc tout l'historique disponible.

select
    transfer_id,
    joueur,
    club_depart,
    club_arrivee,
    montant,
    date_transfert,
    type_transfert,
    _extracted_at

from {{ ref('stg_football_transfers') }}
