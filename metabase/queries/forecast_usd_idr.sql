with last_date as (
    select max(rate_date) as max_date
    from marts.fct_exchange_rates
    where not is_filled
),

actuals as (
    select rates.rate_date, rates.rate as actual
    from marts.fct_exchange_rates as rates
    cross join last_date
    where rates.base_currency = 'USD'
      and rates.quote_currency = 'IDR'
      and not rates.is_filled
      and rates.rate_date >= last_date.max_date - 180
),

forecasts as (
    select forecast_date as rate_date, forecast_rate as moving_average_forecast
    from marts.fct_rate_forecast
    where base_currency = 'USD'
      and quote_currency = 'IDR'
)

select
    coalesce(actuals.rate_date, forecasts.rate_date) as rate_date,
    actuals.actual,
    forecasts.moving_average_forecast
from actuals
full outer join forecasts
    on forecasts.rate_date = actuals.rate_date
order by rate_date
