-- One row per customer and snapshot month. Features use ONLY months before the snapshot
-- (point-in-time correct); the label is whether the customer churns during the snapshot month.
with usage as (
    select
        u.customer_id,
        u.usage_month,
        avg(u.voice_minutes) over w   as avg_voice_minutes_3m,
        avg(u.data_gb) over w         as avg_data_gb_3m,
        sum(u.support_calls) over w   as support_calls_3m,
        count(*) over w               as months_of_history
    from {{ ref('stg_bronze__usage_monthly') }} u
    window w as (partition by u.customer_id order by u.usage_month rows between 3 preceding and 1 preceding)
)

select
    u.customer_id,
    u.usage_month                                                       as snapshot_month,
    c.plan,
    c.monthly_charge_usd,
    {{ dbt.datediff('c.signup_date', 'u.usage_month', 'month') }}       as tenure_months,
    u.avg_voice_minutes_3m,
    u.avg_data_gb_3m,
    u.support_calls_3m,
    u.months_of_history,
    coalesce(c.churn_date >= u.usage_month
             and c.churn_date < u.usage_month + interval 1 month, false) as churned_in_month
from usage u
join {{ ref('stg_bronze__customers') }} c on c.customer_id = u.customer_id
where c.churn_date is null or c.churn_date >= u.usage_month
