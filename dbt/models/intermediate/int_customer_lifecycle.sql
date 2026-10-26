-- First and last active month per customer. A churner's churn month is the first month without service.
select
    u.customer_id,
    min(u.usage_month)                                              as first_month,
    max(u.usage_month)                                              as last_active_month,
    case when any_value(c.churned_by_extract) then max(u.usage_month) + interval 1 month end as churn_month
from {{ ref('stg_usage__monthly') }} u
join {{ ref('stg_telco__customers') }} c using (customer_id)
group by 1
