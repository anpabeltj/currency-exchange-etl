{#
  Every pair between the base currency and all quote currencies.
  Frankfurter gives IDR per USD and MYR per USD, so
  IDR per MYR = (IDR per USD) / (MYR per USD).
#}
with usd_rates as (

    select rate_date, base_currency, quote_currency, rate, is_filled
    from {{ ref('fct_exchange_rates') }}

),

base_legs as (

    {# Add the base currency itself as a leg with rate 1 so USD pairs are included #}
    select distinct
        rate_date,
        base_currency,
        base_currency as quote_currency,
        1::numeric    as rate,
        false         as is_filled
    from usd_rates

),

legs as (

    select * from usd_rates
    union all
    select * from base_legs

)

select
    to_leg.rate_date,
    from_leg.quote_currency                          as from_currency,
    to_leg.quote_currency                            as to_currency,
    round(to_leg.rate / from_leg.rate, 8)            as rate,
    (to_leg.is_filled or from_leg.is_filled)         as is_filled
from legs as to_leg
inner join legs as from_leg
    on  from_leg.rate_date = to_leg.rate_date
    and from_leg.base_currency = to_leg.base_currency
    and from_leg.quote_currency <> to_leg.quote_currency
