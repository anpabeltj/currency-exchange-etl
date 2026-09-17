{#
  Build a complete calendar per currency pair and forward fill weekends and
  holidays with the last published rate.

  Postgres has no "ignore nulls" for last_value, so we use the grouping trick:
  count(rate) only increases on days with a real rate, which puts each
  published day and the empty days after it into the same group.
#}
with rates as (

    select * from {{ ref('stg_frankfurter__rates') }}

),

pair_bounds as (

    select
        base_currency,
        quote_currency,
        min(rate_date) as first_date
    from rates
    group by base_currency, quote_currency

),

last_published as (

    select max(rate_date) as last_date from rates

),

calendar as (

    select
        pair_bounds.base_currency,
        pair_bounds.quote_currency,
        dim_date.date_day as rate_date
    from pair_bounds
    cross join last_published
    inner join {{ ref('dim_date') }} as dim_date
        on dim_date.date_day between pair_bounds.first_date and last_published.last_date

),

joined as (

    select
        calendar.rate_date,
        calendar.base_currency,
        calendar.quote_currency,
        rates.rate as published_rate,
        count(rates.rate) over (
            partition by calendar.base_currency, calendar.quote_currency
            order by calendar.rate_date
        ) as fill_group
    from calendar
    left join rates
        on  rates.rate_date = calendar.rate_date
        and rates.base_currency = calendar.base_currency
        and rates.quote_currency = calendar.quote_currency

)

select
    rate_date,
    base_currency,
    quote_currency,
    first_value(published_rate) over (
        partition by base_currency, quote_currency, fill_group
        order by rate_date
    ) as rate,
    published_rate is null as is_filled
from joined
