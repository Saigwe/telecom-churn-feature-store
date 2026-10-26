-- Customers scored and the share who churn within the label window, per snapshot.
select
    snapshot_month,
    count(*)                                                        as customers,
    count(churned_next_3m)                                          as labelled,
    avg(case when churned_next_3m then 1.0 when churned_next_3m is not null then 0.0 end) as churn_rate_next_3m
from {{ ref('fct_customer_month_features') }}
group by 1
