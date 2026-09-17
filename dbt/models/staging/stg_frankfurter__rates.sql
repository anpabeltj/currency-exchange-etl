{#
  One row per rate_date and currency pair.
  The raw table is append only, so keep the most recently loaded version.
#}
with source as (

    select * from {{ source('frankfurter', 'rates') }}

),

ranked as (

    select
        rate_date,
        upper(trim(base_currency))::char(3)  as base_currency,
        upper(trim(quote_currency))::char(3) as quote_currency,
        rate::numeric(20, 8)                 as rate,
        provider,
        loaded_at,
        row_number() over (
            partition by rate_date, upper(trim(base_currency)), upper(trim(quote_currency))
            order by loaded_at desc, raw_id desc
        ) as version_rank
    from source

)

select
    rate_date,
    base_currency,
    quote_currency,
    rate,
    provider,
    loaded_at
from ranked
where version_rank = 1
