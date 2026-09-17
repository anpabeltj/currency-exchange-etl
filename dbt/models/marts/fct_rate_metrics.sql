{#
  Metrics use published days only. Forward filled weekend rows would add fake
  zero returns and make volatility look lower than it really is.
  Windows are counted in published days, not calendar days.
#}
{% set window_size = var('anomaly_window_size') %}

with published as (

    select rate_date, base_currency, quote_currency, rate
    from {{ ref('fct_exchange_rates') }}
    where not is_filled

),

returns as (

    select
        rate_date,
        base_currency,
        quote_currency,
        rate,
        lag(rate) over pair_window as previous_rate,
        ln(rate / lag(rate) over pair_window) as log_return
    from published
    window pair_window as (
        partition by base_currency, quote_currency
        order by rate_date
    )

),

rolling as (

    select
        *,
        avg(rate) over (pair_window rows between 6 preceding and current row)  as moving_avg_7d,
        avg(rate) over (pair_window rows between 29 preceding and current row) as moving_avg_30d,
        stddev_samp(log_return) over (pair_window rows between 29 preceding and current row) as volatility_30d,
        avg(log_return) over (
            pair_window rows between {{ window_size }} preceding and 1 preceding
        ) as trailing_mean_return,
        stddev_samp(log_return) over (
            pair_window rows between {{ window_size }} preceding and 1 preceding
        ) as trailing_std_return,
        count(log_return) over (
            pair_window rows between {{ window_size }} preceding and 1 preceding
        ) as trailing_observations
    from returns
    window pair_window as (
        partition by base_currency, quote_currency
        order by rate_date
    )

),

scored as (

    select
        *,
        case
            when trailing_observations >= {{ window_size }} and trailing_std_return > 0
            then (log_return - trailing_mean_return) / trailing_std_return
        end as return_z_score
    from rolling

)

select
    rate_date,
    base_currency,
    quote_currency,
    rate,
    previous_rate,
    round((rate / previous_rate - 1) * 100, 4) as pct_change,
    log_return,
    round(moving_avg_7d, 8)                     as moving_avg_7d,
    round(moving_avg_30d, 8)                    as moving_avg_30d,
    volatility_30d,
    round(return_z_score, 4)                    as return_z_score,
    coalesce(abs(return_z_score) >= {{ var('anomaly_z_threshold') }}, false) as is_anomaly
from scored
