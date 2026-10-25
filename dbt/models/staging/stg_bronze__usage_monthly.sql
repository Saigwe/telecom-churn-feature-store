select
    customer_id,
    cast(usage_month as date)             as usage_month,
    voice_minutes,
    data_gb,
    support_calls
from {{ source('bronze', 'usage_monthly') }}
