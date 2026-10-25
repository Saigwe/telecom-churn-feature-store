select
    customer_id,
    cast(signup_date as date)                  as signup_date,
    plan,
    monthly_charge_usd,
    cast(churn_date as date)                   as churn_date
from {{ source('bronze', 'customers') }}
