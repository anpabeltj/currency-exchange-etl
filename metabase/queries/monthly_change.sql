with month_end_rates as (
    select distinct on (quote_currency, date_trunc('month', rate_date))
        quote_currency,
        date_trunc('month', rate_date)::date as month,
        rate
    from marts.fct_exchange_rates
    where base_currency = 'USD'
    order by quote_currency, date_trunc('month', rate_date), rate_date desc
),

changes as (
    select
        month,
        quote_currency,
        round((rate / lag(rate) over (partition by quote_currency order by month) - 1) * 100, 2) as pct_change
    from month_end_rates
)

select month, quote_currency, pct_change
from changes
where pct_change is not null
  and month >= date_trunc('month', current_date) - interval '24 months'
order by month, quote_currency
