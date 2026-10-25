-- Leakage guard: the first snapshot month has no history, so its features must be empty.
select *
from {{ ref('fct_customer_month_features') }}
where months_of_history = 0 and avg_voice_minutes_3m is not null
