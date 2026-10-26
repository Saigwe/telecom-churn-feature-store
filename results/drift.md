# Feature drift: training snapshots vs the scoring snapshot

Reference: 26,015 rows (snapshots 2025-01 to 2025-05). Current: 5,163 rows (2026-01). Full report: `drift_report.html`.

- Drifted columns: 8 of 26 (charge_change_vs_6m, tenure_months, charge_last_month, charge_avg_6m, data_gb_avg_3m, days_late_3m, support_tickets_3m, total_charges_to_date)
- Control (training months split in half by customer): 0 of 26 columns drifted

| Column | Drift score (current) | Drift score (control) |
|---|---:|---:|
| charge_change_vs_6m | 0.415 | 0.025 |
| tenure_months | 0.241 | 0.024 |
| charge_last_month | 0.216 | 0.049 |
| charge_avg_6m | 0.215 | 0.049 |
| data_gb_avg_3m | 0.159 | 0.027 |
| days_late_3m | 0.140 | 0.012 |
| support_tickets_3m | 0.139 | 0.024 |
| total_charges_to_date | 0.123 | 0.016 |
| internet_service | 0.075 | 0.015 |
| payment_method | 0.062 | 0.010 |
| has_multiple_lines | 0.059 | 0.019 |
| has_streaming_tv | 0.054 | 0.003 |
| has_streaming_movies | 0.053 | 0.005 |
| voice_minutes_avg_3m | 0.045 | 0.010 |
| is_paperless | 0.043 | 0.012 |
| data_gb_trend | 0.040 | 0.026 |
| is_senior | 0.038 | 0.005 |
| has_device_protection | 0.035 | 0.017 |
| has_online_backup | 0.028 | 0.010 |
| has_partner | 0.024 | 0.003 |
| voice_minutes_trend | 0.018 | 0.024 |
| has_tech_support | 0.009 | 0.008 |
| has_dependents | 0.008 | 0.007 |
| has_online_security | 0.007 | 0.003 |
| contract | 0.006 | 0.006 |
| has_phone | 0.003 | 0.010 |
