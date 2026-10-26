-- Leakage test, two ways:
--  1. no feature row read a month at or after its snapshot
--  2. recompute total charges and tickets independently from usage strictly before the snapshot; they must match
with recomputed as (
    select f.customer_id, f.snapshot_month,
           sum(u.monthly_charge_usd)                                  as total_charges,
           sum(u.support_tickets) filter (where u.usage_month >= f.snapshot_month - interval 3 month) as tickets_3m
    from {{ ref('fct_customer_month_features') }} f
    join {{ ref('stg_usage__monthly') }} u
      on u.customer_id = f.customer_id and u.usage_month < f.snapshot_month
    group by 1, 2
)
select customer_id, snapshot_month, 'read the snapshot month or later' as problem
from {{ ref('fct_customer_month_features') }}
where feature_cutoff_month >= snapshot_month
union all
select f.customer_id, f.snapshot_month, 'feature differs from an independent point-in-time recompute'
from {{ ref('fct_customer_month_features') }} f
join recomputed r using (customer_id, snapshot_month)
where abs(f.total_charges_to_date - r.total_charges) > 0.01 or f.support_tickets_3m <> coalesce(r.tickets_3m, 0)
