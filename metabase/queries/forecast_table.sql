select
    forecast_date,
    business_days_ahead,
    max(case when quote_currency = 'IDR' then forecast_rate end) as usd_to_idr,
    max(case when quote_currency = 'MYR' then forecast_rate end) as usd_to_myr,
    max(case when quote_currency = 'SGD' then forecast_rate end) as usd_to_sgd
from marts.fct_rate_forecast
where base_currency = 'USD'
group by forecast_date, business_days_ahead
order by forecast_date
