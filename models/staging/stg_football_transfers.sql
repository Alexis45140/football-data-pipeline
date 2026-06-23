SELECT 
    *
FROM {{ source('raw_football', 'stg_transferts') }}