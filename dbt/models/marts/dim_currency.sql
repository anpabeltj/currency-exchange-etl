select
    currency_code,
    currency_name,
    country,
    region
from {{ ref('currencies') }}
