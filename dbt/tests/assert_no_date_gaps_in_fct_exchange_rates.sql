{#
  After forward filling, every currency pair must have exactly one row per
  calendar day between its first and last date. Returns the pairs that do not.
#}
select
    base_currency,
    quote_currency,
    count(*) as row_count,
    (max(rate_date) - min(rate_date) + 1) as expected_days
from {{ ref('fct_exchange_rates') }}
group by base_currency, quote_currency
having count(*) <> (max(rate_date) - min(rate_date) + 1)
