-- One row per customer per active month (charges real-derived, usage synthetic: see ingestion/load_telco.py).
select
    customer_id,
    cast(usage_month as date)                                       as usage_month,
    cast(monthly_charge_usd as double)                              as monthly_charge_usd,
    cast(data_gb as double)                                         as data_gb,
    cast(voice_minutes as double)                                   as voice_minutes,
    cast(support_tickets as integer)                                as support_tickets,
    cast(days_late as integer)                                      as days_late
from {{ source('bronze', 'usage_monthly') }}
