# 3-minute walkthrough: Telecom Churn Feature Store

A timed script for a Loom recording of about 3 minutes (screen plus camera bubble, 1080p). Say it in your own words; the lines are a guide, not a teleprompter.

**Open these tabs before you press record:** README, dbt/models, feature_repo/, results/model_comparison.md, results/drift_report.html.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | Portfolio card, then the README title | Churn models look great in a notebook and disappoint in production. This pipeline proves that training and serving are identical, and measures exactly how much leakage would have overstated the model. |
| 0:20–0:45 | README intro and the Data section | At a Big Four firm I designed churn-propensity and next-best-offer models for a telecoms operator, with auditable validation. This rebuilds it on the public IBM Telco data. No client data is used. |
| 0:45–1:10 | The point-in-time features and leakage test in `dbt/` | Features read only earlier months, and a dbt test recomputes them that way and must match. |
| 1:10–1:35 | `feature_repo/` and the MLflow registry | Feast builds training sets with its point-in-time join and serves the same features online. The champion is registered in MLflow. |
| 1:35–2:00 | `results/model_comparison.md` and `results/drift.md` | With leaky columns swapped in, PR AUC jumps from 0.309 to 0.515. That's what a non-point-in-time table would have claimed. |
| 2:00–2:30 | Consistency checks in Numbers | Feast reproduces the dbt features on all 41,341 training rows, and the online store matches offline for all 5,163 scored customers, with 0 mismatches. The README says plainly that the monthly usage behind the 0.913 ROC AUC champion is synthetic. |
| 2:30–2:45 | `docs/design_doc.md`, the options table | The decision I'd defend in an interview: Measure leakage rather than just avoid it, so the honest model's lower score is defensible. |
| 2:45–3:00 | Back to the README top | For a retention team, that means a ranked list they can trust, scored in production exactly as in training. The repo, numbers and design doc are linked under the video. |

## Recording checklist
- Close email, chat and notifications. Zoom the browser to 125% so code is readable.
- Run `make fixture-all` once before recording, so CI-style output is fresh if you show it.
- Keep to one take per section; Loom lets you trim. Aim for 2:45 to 3:10.
- Show real numbers on screen as you say them; never estimate on camera.
- Say "synthetic" out loud wherever the README labels data as synthetic.

## After recording
1. Copy the Loom share link.
2. In `README.md`, replace the roadmap line with `- [x] [3-minute Loom walkthrough](<your Loom link>)` and add the link under the title.
3. Add the link to this project's card on saigwe.github.io.
