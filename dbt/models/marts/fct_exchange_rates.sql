{{
  config(
    materialized='incremental',
    unique_key=['rate_date', 'base_currency', 'quote_currency'],
    incremental_strategy='delete+insert',
    on_schema_change='fail'
  )
}}

{#
  Incremental logic
  Every row stores source_watermark, the newest raw loaded_at seen when it was built.
  On the next run we find the earliest rate_date among raw rows loaded after that
  watermark and rebuild everything from that date forward.

  This picks up three cases without a full refresh:
    new days from the daily run
    revised rates inside the Airflow lookback window
    historical backfills triggered with start_date and end_date params

  Rebuilding forward from the earliest changed date matters because a revised
  Friday rate also changes the forward filled Saturday and Sunday rows.
#}

with filled as (

    select * from {{ ref('int_rates__date_filled') }}

),

watermark as (

    select max(loaded_at) as source_watermark
    from {{ ref('stg_frankfurter__rates') }}

)

{% if is_incremental() %}
, rebuild_from as (

    select min(rate_date) as rebuild_date
    from {{ ref('stg_frankfurter__rates') }}
    where loaded_at > (select max(source_watermark) from {{ this }})

)
{% endif %}

select
    filled.rate_date,
    filled.base_currency,
    filled.quote_currency,
    filled.rate,
    filled.is_filled,
    watermark.source_watermark,
    current_timestamp as dbt_updated_at
from filled
cross join watermark

{% if is_incremental() %}
where filled.rate_date >= (select rebuild_date from rebuild_from)
{% endif %}
