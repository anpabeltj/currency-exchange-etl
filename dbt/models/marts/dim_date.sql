with bounds as (

    select
        min(rate_date)                          as start_date,
        greatest(max(rate_date), current_date)  as end_date
    from {{ ref('stg_frankfurter__rates') }}

),

days as (

    select generate_series(start_date, end_date, interval '1 day')::date as date_day
    from bounds

)

select
    date_day,
    extract(year from date_day)::int     as year,
    extract(quarter from date_day)::int  as quarter,
    extract(month from date_day)::int    as month,
    trim(to_char(date_day, 'Month'))     as month_name,
    extract(week from date_day)::int     as iso_week,
    extract(isodow from date_day)::int   as day_of_week,
    trim(to_char(date_day, 'Day'))       as day_name,
    extract(isodow from date_day) in (6, 7) as is_weekend
from days
