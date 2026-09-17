select rate as usd_to_idr
from marts.fct_exchange_rates
where base_currency = 'USD'
  and quote_currency = 'IDR'
order by rate_date desc
limit 1
