# Design doc: Telecom Churn Feature Store

| | |
|---|---|
| **Author** | Stanley Igwe |
| **Status** | Core build complete on the IBM Telco data |
| **Last updated** | 2026-10-26 |

## 1. Problem and users
- **Users:** retention and CRM teams who act on a monthly list of at-risk customers; data scientists who build the models.
- **Questions they need answered:** Who is likely to leave in the next three months, how sure are we, and has the customer base changed since the model was trained?
- **Current pain (scenario):** a model scored 0.85 AUC offline because its features used end-of-period totals, and lift halved in production. Scoring features were recomputed in a different script from training.

## 2. Requirements
| Type | Requirement |
|---|---|
| Functional | Monthly point-in-time features, a 3-month churn label, model training and registry, batch scoring, drift report. |
| Correctness | No feature reads data at or after its snapshot (tested); offline and online features are identical (tested). |
| Freshness / SLA | Monthly snapshot; scoring reads the online store, so a real-time API can reuse it unchanged. |
| Scale | 67k feature rows and a 1-minute training run on a laptop; Feast and MLflow swap to cloud stores (BigQuery or Snowflake offline, Redis or DynamoDB online, a hosted MLflow) without code changes. |

## 3. Design
- **Layers:** bronze (IBM file + derived history) → silver (typed) → gold point-in-time feature table → Feast (offline Parquet, online SQLite) → MLflow → scores back in gold.
- **Key choices:** a feature row's `event_timestamp` is its snapshot month, because its features use months before it; Feast's own point-in-time join then matches dbt by construction (verified). Training uses only snapshots whose label windows have closed, and the test is out of time. The champion is chosen by an alias in the registry, so serving code never names a version.

## 4. Options considered
| Decision | Options | Chosen | Why |
|---|---|---|---|
| Where features are computed | Python in the training script; dbt | dbt | Tested SQL, one definition for training and serving; Feast only stores and serves. |
| Validation | Random split; out-of-time with a label gap | Out of time | Random splits leak the future through repeated customers and seasonality. |
| Model | Logistic regression; gradient boosting | Both tracked; best registered | On real-derived features logistic regression wins; boosting wins once usage is added. |
| Model serialisation | Pickle; skops (MLflow 3 default) | skops, two types explicitly trusted | Safer to load; trusting only the types our own pipeline uses. |

## 5. Risks and what I'd change at 10x scale
- The monthly usage is synthetic with planted signal, so the champion's lift over real-only features is illustrative. Real usage data is the first thing to plug in.
- Contract and services are known only as of the IBM snapshot and are treated as constant; real systems need their history as SCD2.
- At 10x: incremental dbt snapshots, a cloud offline store and Redis online, scheduled retraining when drift crosses a threshold, and a REST endpoint over the online store.
