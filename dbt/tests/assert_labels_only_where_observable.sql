-- A label exists only when its whole window is observed, and churners are labelled positive exactly once
-- per snapshot window (no customer churns twice).
select customer_id, snapshot_month
from {{ ref('fct_customer_month_features') }}
where (churned_next_3m is null) <> (snapshot_month + interval {{ var('label_horizon_months') }} month
                                    > date '{{ var("data_end_month") }}' + interval 1 month)
