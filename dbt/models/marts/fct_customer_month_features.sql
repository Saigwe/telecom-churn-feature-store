-- One row per customer per monthly snapshot, for every customer active in the month before the snapshot.
-- POINT-IN-TIME RULE: every usage feature reads only months strictly before snapshot_month, and
-- feature_cutoff_month records the latest month actually read (tests assert it is < snapshot_month).
-- Label: churned_next_3m = the churn month falls in [snapshot, snapshot + 3 months); null when the window
-- runs past the observed data (those rows are for scoring, not training).
{% set horizon = var('label_horizon_months') %}
with snapshots as (
    select cast(s as date) as snapshot_month
    from generate_series(date '{{ var("first_snapshot") }}', date '{{ var("last_snapshot") }}', interval 1 month) as t(s)
),
eligible as (
    select l.customer_id, s.snapshot_month, l.first_month, l.churn_month
    from snapshots s
    join {{ ref('int_customer_lifecycle') }} l
      on l.first_month < s.snapshot_month and l.last_active_month >= s.snapshot_month - interval 1 month
),
history as (
    select
        e.customer_id,
        e.snapshot_month,
        max(u.usage_month)                                                                  as feature_cutoff_month,
        count(*)                                                                            as tenure_months,
        sum(u.monthly_charge_usd)                                                           as total_charges_to_date,
        max(u.monthly_charge_usd) filter (where u.usage_month = e.snapshot_month - interval 1 month) as charge_last_month,
        avg(u.monthly_charge_usd) filter (where u.usage_month >= e.snapshot_month - interval 6 month) as charge_avg_6m,
        avg(u.data_gb) filter (where u.usage_month >= e.snapshot_month - interval 3 month)  as data_gb_avg_3m,
        avg(u.data_gb) filter (where u.usage_month between e.snapshot_month - interval 6 month
                                                       and e.snapshot_month - interval 4 month) as data_gb_avg_prior_3m,
        avg(u.voice_minutes) filter (where u.usage_month >= e.snapshot_month - interval 3 month) as voice_minutes_avg_3m,
        avg(u.voice_minutes) filter (where u.usage_month between e.snapshot_month - interval 6 month
                                                             and e.snapshot_month - interval 4 month) as voice_minutes_avg_prior_3m,
        coalesce(sum(u.support_tickets) filter (where u.usage_month >= e.snapshot_month - interval 3 month), 0) as support_tickets_3m,
        coalesce(sum(u.days_late) filter (where u.usage_month >= e.snapshot_month - interval 3 month), 0) as days_late_3m
    from eligible e
    join {{ ref('stg_usage__monthly') }} u
      on u.customer_id = e.customer_id and u.usage_month < e.snapshot_month
    group by 1, 2
)
select
    h.customer_id,
    h.snapshot_month,
    h.feature_cutoff_month,
    -- point-in-time behaviour (charges real-derived; usage synthetic)
    h.tenure_months,
    h.total_charges_to_date,
    h.charge_last_month,
    h.charge_avg_6m,
    h.charge_last_month - h.charge_avg_6m                                                   as charge_change_vs_6m,
    h.data_gb_avg_3m,
    h.data_gb_avg_3m / nullif(h.data_gb_avg_prior_3m, 0)                                    as data_gb_trend,
    h.voice_minutes_avg_3m,
    h.voice_minutes_avg_3m / nullif(h.voice_minutes_avg_prior_3m, 0)                        as voice_minutes_trend,
    h.support_tickets_3m,
    h.days_late_3m,
    -- static attributes (as of the IBM snapshot)
    c.is_senior, c.has_partner, c.has_dependents, c.has_phone, c.has_multiple_lines, c.internet_service,
    c.has_online_security, c.has_online_backup, c.has_device_protection, c.has_tech_support,
    c.has_streaming_tv, c.has_streaming_movies, c.contract, c.is_paperless, c.payment_method,
    -- label
    case when e.snapshot_month + interval {{ horizon }} month > date '{{ var("data_end_month") }}' + interval 1 month then null
         else coalesce(e.churn_month >= e.snapshot_month
                       and e.churn_month < e.snapshot_month + interval {{ horizon }} month, false)
    end                                                                                     as churned_next_3m
from history h
join eligible e using (customer_id, snapshot_month)
join {{ ref('stg_telco__customers') }} c using (customer_id)
