{{ config(
    materialized='incremental',
    unique_key='transfer_id',
    incremental_strategy='merge',
    partition_by={'field': 'date_transfert', 'data_type': 'timestamp', 'granularity': 'month'},
    cluster_by=['type_transfert']
) }}

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

{% if is_incremental() %}

    -- On ne relit que les lignes arrivees depuis le dernier run, le merge
    -- se charge de mettre a jour un transfert deja present.
    where _extracted_at > (
        select coalesce(max(_extracted_at), timestamp('1970-01-01'))
        from {{ this }}
    )

{% endif %}
