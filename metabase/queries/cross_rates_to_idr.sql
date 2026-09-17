select
    rate_date,
    max(case when from_currency = 'MYR' then rate end) as myr_to_idr,
    max(case when from_currency = 'SGD' then rate end) as sgd_to_idr
from marts.fct_cross_rates
where to_currency = 'IDR'
  and from_currency in ('MYR', 'SGD')
group by rate_date
order by rate_date
