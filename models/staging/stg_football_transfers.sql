{{ config(materialized='view') }}

with source as (

    select * from {{ source('raw_football', 'transfers_raw') }}

),

typed as (

    select
        to_hex(md5(concat(
            coalesce(joueur, ''), '|',
            coalesce(club_arrivee, ''), '|',
            coalesce(date_transfert, '')
        ))) as transfer_id,
        joueur,
        club_depart,
        club_arrivee,
        cast(montant as float64) as montant,
        -- SAFE. : l'API a deja renvoye des dates hors format, on ne veut pas planter le run
        safe.parse_timestamp('%Y-%m-%dT%H:%M:%SZ', date_transfert) as date_transfert,
        type_transfert,
        _extracted_at

    from source

),

-- Le meme transfert revient a chaque run tant qu'il est dans la fenetre de l'API
deduplicated as (

    select * except (rn)
    from (
        select
            *,
            row_number() over (
                partition by transfer_id
                order by _extracted_at desc
            ) as rn
        from typed
    )
    where rn = 1

)

select * from deduplicated
