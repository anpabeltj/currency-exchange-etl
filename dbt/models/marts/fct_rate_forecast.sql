{#
  Moving average forecast.
  For each currency pair, the forecast is the average of the last
  forecast_window_size published rates, repeated for the next
  forecast_horizon business days. ECB holidays are not excluded.

  This is a simple baseline, not a machine learning model.
#}
{% set window_size = var('forecast_window_size') %}
{% set horizon = var('forecast_horizon') %}

with published as (

    select
        base_currency,
        quote_currency,
        rate_date,
        rate,
        row_number() over (
            partition by base_currency, quote_currency
            order by rate_date desc
        ) as recency_rank
    from {{ ref('fct_exchange_rates') }}
    where not is_filled

),

moving_average as (

    select
        base_currency,
        quote_currency,
        max(rate_date)        as last_rate_date,
        min(rate_date)        as window_start_date,
        round(avg(rate), 8)   as forecast_rate
    from published
    where recency_rank <= {{ window_size }}
    group by base_currency, quote_currency

),

future_business_days as (

    select
        moving_average.*,
        calendar_day::date as forecast_date,
        row_number() over (
            partition by moving_average.base_currency, moving_average.quote_currency
            order by calendar_day
        ) as business_days_ahead
    from moving_average
    cross join lateral generate_series(
        moving_average.last_rate_date + 1,
        moving_average.last_rate_date + {{ horizon * 2 }},
        interval '1 day'
    ) as calendar_day
    where extract(isodow from calendar_day) < 6

)

select
    forecast_date,
    base_currency,
    quote_currency,
    forecast_rate,
    business_days_ahead,
    window_start_date,
    last_rate_date
from future_business_days
where business_days_ahead <= {{ horizon }}