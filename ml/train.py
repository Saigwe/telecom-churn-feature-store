"""Build the training set from Feast (point-in-time join), train four models, track them in MLflow, register the
best honest one as telecom_churn@champion.

  logreg_real   logistic regression, real-derived features only (profile + tenure + charges)
  hgb_real      gradient boosting, real-derived features only
  hgb_all       gradient boosting, real-derived + synthetic usage features (planted signal: read with care)
  hgb_leaky     hgb_real, but with the as-of-extract tenure and TotalCharges instead of the point-in-time ones:
                what happens when a feature table isn't point-in-time. Never registered.

Split: train on snapshots January-May 2025 (label windows closed by August), test on August-October 2025.

Usage: python ml/train.py --db warehouse/churn.duckdb --out results/model_comparison.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CATEGORICAL, FEAST_FEATURES, FLAGS, MODEL_NAME, REAL_NUMERIC, ROOT, SKOPS_TRUSTED_TYPES,  # noqa: E402
                    SYNTHETIC_NUMERIC, TEST_SNAPSHOTS, TRAIN_SNAPSHOTS, pipeline, store, tracking_uri)


def lift_at(y, p, share=0.1) -> float:
    k = max(1, int(len(p) * share))
    top = np.argsort(-p)[:k]
    return float(y[top].mean() / y.mean())


def metrics(y, p) -> dict:
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "lift_top_decile": lift_at(y, p), "brier": brier_score_loss(y, p)}


def training_frame(db: str) -> pd.DataFrame:
    con = duckdb.connect(db, read_only=True)
    labels = con.execute(f"""
        select f.customer_id, timezone('UTC', cast(f.snapshot_month as timestamp)) as event_timestamp,
               f.churned_next_3m::int as churned, c.extract_tenure_months, c.extract_total_charges
        from gold.fct_customer_month_features f
        join silver.stg_telco__customers c using (customer_id)
        where f.churned_next_3m is not null
          and (f.snapshot_month between date '{TRAIN_SNAPSHOTS[0]}' and date '{TRAIN_SNAPSHOTS[1]}'
               or f.snapshot_month between date '{TEST_SNAPSHOTS[0]}' and date '{TEST_SNAPSHOTS[1]}')
    """).df()
    feast_df = store().get_historical_features(entity_df=labels, features=FEAST_FEATURES).to_df()
    # Feast returns rows in no fixed order; sort so the early-stopping split, and so the scores, are reproducible
    feast_df = feast_df.sort_values(["event_timestamp", "customer_id"], ignore_index=True)
    dbt_df = con.execute("select customer_id, timezone('UTC', cast(snapshot_month as timestamp)) as event_timestamp, "
                         f"{', '.join(REAL_NUMERIC + SYNTHETIC_NUMERIC)} from gold.fct_customer_month_features").df()
    check = feast_df.merge(dbt_df, on=["customer_id", "event_timestamp"], suffixes=("", "_dbt"))
    cols = REAL_NUMERIC + SYNTHETIC_NUMERIC
    same = np.all([np.isclose(check[c].astype(float), check[f"{c}_dbt"].astype(float), equal_nan=True) for c in cols], axis=0)
    feast_df.attrs["feast_vs_dbt_mismatches"] = int((~same).sum()) + (len(feast_df) - len(check))
    return feast_df


def main() -> None:
    import mlflow
    from mlflow.tracking import MlflowClient
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="warehouse/churn.duckdb")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results" / "model_comparison.md")
    args = ap.parse_args()

    df = training_frame(args.db)
    df[FLAGS] = df[FLAGS].astype(float)
    df[CATEGORICAL] = df[CATEGORICAL].astype(str)
    ts = df.event_timestamp.dt.tz_convert(None)
    train = df[ts <= TRAIN_SNAPSHOTS[1]]
    test = df[ts >= TEST_SNAPSHOTS[0]]
    leaky = df.assign(tenure_months=df.extract_tenure_months, total_charges_to_date=df.extract_total_charges)

    # Each customer appears in up to five training snapshots, so trees overfit easily: keep leaves large and stop
    # early on a validation split drawn from the TRAINING months only (the test months are never looked at).
    hgb = lambda: HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, max_leaf_nodes=15,
                                                 min_samples_leaf=200, l2_regularization=1.0, early_stopping=True,
                                                 validation_fraction=0.2, n_iter_no_change=20, random_state=0)
    candidates = {
        "logreg_real": (REAL_NUMERIC, LogisticRegression(max_iter=2000, C=0.5), df),
        "hgb_real": (REAL_NUMERIC, hgb(), df),
        "hgb_all": (REAL_NUMERIC + SYNTHETIC_NUMERIC, hgb(), df),
        "hgb_leaky": (REAL_NUMERIC, hgb(), leaky),
    }
    mlflow.set_tracking_uri(tracking_uri())
    mlflow.set_experiment("telecom-churn")
    results, versions = {}, {}
    for name, (numeric, estimator, frame) in candidates.items():
        cols = numeric + FLAGS + CATEGORICAL
        tr, te = frame.loc[train.index], frame.loc[test.index]
        model = pipeline(numeric, estimator).fit(tr[cols], tr.churned)
        m = metrics(te.churned.to_numpy(), model.predict_proba(te[cols])[:, 1])
        results[name] = m
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({"model": name, "features": len(cols), "train_rows": len(tr), "test_rows": len(te),
                               "train_snapshots": "..".join(TRAIN_SNAPSHOTS), "test_snapshots": "..".join(TEST_SNAPSHOTS),
                               "uses_synthetic_usage": name == "hgb_all", "leaky": name == "hgb_leaky"})
            mlflow.log_metrics({f"test_{k}": v for k, v in m.items()})
            mlflow.log_metric("feast_vs_dbt_mismatches", df.attrs["feast_vs_dbt_mismatches"])
            if name != "hgb_leaky":
                info = mlflow.sklearn.log_model(model, name="model", input_example=te[cols].head(5),
                                                skops_trusted_types=SKOPS_TRUSTED_TYPES,
                                                registered_model_name=MODEL_NAME)
                versions[name] = info.registered_model_version
        print(f"{name:12s} " + "  ".join(f"{k}={v:.3f}" for k, v in m.items()))

    champion = max((n for n in versions), key=lambda n: results[n]["roc_auc"])
    client = MlflowClient()
    client.set_registered_model_alias(MODEL_NAME, "champion", versions[champion])
    client.set_registered_model_alias(MODEL_NAME, "real_features_only", versions["hgb_real"])

    base = float(test.churned.mean())
    lines = [
        "# Churn models: out-of-time test",
        "",
        f"Training set built by Feast's point-in-time join: {len(train):,} rows (snapshots {TRAIN_SNAPSHOTS[0][:7]} to "
        f"{TRAIN_SNAPSHOTS[1][:7]}), test {len(test):,} rows ({TEST_SNAPSHOTS[0][:7]} to {TEST_SNAPSHOTS[1][:7]}). "
        f"Test churn rate within 3 months: {base:.1%}. Feast vs dbt feature mismatches: {df.attrs['feast_vs_dbt_mismatches']}.",
        "",
        "| Model | Features | ROC AUC | PR AUC | Lift, top 10% | Brier |",
        "|---|---|---:|---:|---:|---:|",
    ]
    label = {"logreg_real": "real-derived", "hgb_real": "real-derived", "hgb_all": "real + synthetic usage",
             "hgb_leaky": "real-derived, but as-of-extract tenure and charges (LEAKY)"}
    for n, m in results.items():
        lines.append(f"| {n}{' (champion)' if n == champion else ''} | {label[n]} | {m['roc_auc']:.3f} | {m['pr_auc']:.3f} "
                     f"| {m['lift_top_decile']:.2f}x | {m['brier']:.4f} |")
    lines += ["", "Usage features (data, minutes, tickets, late days) are synthetic with planted pre-churn drift, so "
                  "`hgb_all`'s gain over `hgb_real` shows the pipeline uses them, not what real usage would add. "
                  "`hgb_leaky` is `hgb_real` with two columns swapped for their December 2025 extract values; the "
                  "gap between them is what a non-point-in-time feature table would overstate. It is never registered."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out.with_suffix(".json")).write_text(json.dumps({"champion": champion, "results": results,
                                                           "feast_vs_dbt_mismatches": df.attrs["feast_vs_dbt_mismatches"],
                                                           "train_rows": len(train), "test_rows": len(test),
                                                           "test_base_rate": base}, indent=1))
    print(f"champion: {champion} (version {versions[champion]})")


if __name__ == "__main__":
    main()
