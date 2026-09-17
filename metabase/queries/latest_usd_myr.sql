select rate as usd_to_myr
from marts.fct_exchange_rates
where base_currency = 'USD'
  and quote_currency = 'MYR'
order by rate_date desc
limit 1
