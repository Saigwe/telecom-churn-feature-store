# Churn models: out-of-time test

Training set built by Feast's point-in-time join: 26,015 rows (snapshots 2025-01 to 2025-05), test 15,326 rows (2025-08 to 2025-10). Test churn rate within 3 months: 7.6%. Feast vs dbt feature mismatches: 0.

| Model | Features | ROC AUC | PR AUC | Lift, top 10% | Brier |
|---|---|---:|---:|---:|---:|
| logreg_real | real-derived | 0.842 | 0.317 | 4.22x | 0.0603 |
| hgb_real | real-derived | 0.815 | 0.309 | 3.93x | 0.0662 |
| hgb_all (champion) | real + synthetic usage | 0.913 | 0.621 | 6.42x | 0.0442 |
| hgb_leaky | real-derived, but as-of-extract tenure and charges (LEAKY) | 0.853 | 0.515 | 4.77x | 0.0549 |

Usage features (data, minutes, tickets, late days) are synthetic with planted pre-churn drift, so `hgb_all`'s gain over `hgb_real` shows the pipeline uses them, not what real usage would add. `hgb_leaky` is `hgb_real` with two columns swapped for their December 2025 extract values; the gap between them is what a non-point-in-time feature table would overstate. It is never registered.
