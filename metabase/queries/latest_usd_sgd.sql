select rate as usd_to_sgd
from marts.fct_exchange_rates
where base_currency = 'USD'
  and quote_currency = 'SGD'
order by rate_date desc
limit 1
