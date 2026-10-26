"""Batch scoring through the online path: materialise the latest snapshot into Feast's online store, read every
active customer's features online, check them against the offline rows (training-serving consistency), score
with telecom_churn@champion from the MLflow registry, and write gold.churn_scores.

Usage: python ml/score.py --db warehouse/churn.duckdb --out results/scoring.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CATEGORICAL, FEAST_FEATURES, FLAGS, MODEL_NAME, REAL_NUMERIC, ROOT, SCORING_SNAPSHOT,  # noqa: E402
                    SYNTHETIC_NUMERIC, store, tracking_uri)


def main() -> None:
    import mlflow

    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse/churn.duckdb")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results" / "scoring.md")
    args = ap.parse_args()

    snapshot = datetime.fromisoformat(SCORING_SNAPSHOT).replace(tzinfo=timezone.utc)
    fs = store()
    fs.materialize(start_date=snapshot - timedelta(days=1), end_date=snapshot + timedelta(seconds=1))

    offline = pd.read_parquet(ROOT / "data" / "feast" / "customer_month_features.parquet")
    offline = offline[offline.snapshot_month.astype(str) == SCORING_SNAPSHOT].set_index("customer_id")
    online = fs.get_online_features(features=FEAST_FEATURES,
                                    entity_rows=[{"customer_id": c} for c in offline.index]).to_df().set_index("customer_id")
    numeric = REAL_NUMERIC + SYNTHETIC_NUMERIC
    joined = online[numeric].join(offline[numeric], rsuffix="_offline")
    same = np.all([np.isclose(joined[c].astype(float), joined[f"{c}_offline"].astype(float), equal_nan=True)
                   for c in numeric], axis=0)
    mismatches = int((~same).sum())

    mlflow.set_tracking_uri(tracking_uri())
    version = mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
    X = online.reset_index()
    X[FLAGS] = X[FLAGS].astype(float)
    X[CATEGORICAL] = X[CATEGORICAL].astype(str)
    X["churn_probability"] = model.predict_proba(X[numeric + FLAGS + CATEGORICAL])[:, 1]
    X["risk_decile"] = 10 - pd.qcut(X.churn_probability.rank(method="first"), 10, labels=False)
    X["snapshot_month"] = pd.Timestamp(SCORING_SNAPSHOT).date()
    X["model_version"] = int(version.version)
    scores = X[["customer_id", "snapshot_month", "churn_probability", "risk_decile", "model_version", "contract"]]

    con = duckdb.connect(args.db)
    con.execute("create or replace table gold.churn_scores as select * from scores")
    top = scores[scores.risk_decile == 1]
    summary = {
        "snapshot": SCORING_SNAPSHOT, "customers_scored": len(scores), "model_version": int(version.version),
        "online_vs_offline_mismatches": mismatches, "expected_churners_next_3m": float(scores.churn_probability.sum()),
        "top_decile_customers": len(top), "top_decile_mean_probability": float(top.churn_probability.mean()),
        "top_decile_month_to_month_share": float((top.contract == "Month-to-month").mean()),
    }
    lines = [
        "# Batch scoring",
        "",
        f"- Snapshot {SCORING_SNAPSHOT[:7]} (features through December 2025), {len(scores):,} active customers, "
        f"model `{MODEL_NAME}` version {version.version} (alias `champion`).",
        f"- Features read from Feast's online store; online vs offline mismatches: {mismatches}.",
        f"- Expected churners in the next 3 months (sum of probabilities): {summary['expected_churners_next_3m']:.0f}.",
        f"- Top risk decile: {len(top):,} customers, mean probability {summary['top_decile_mean_probability']:.1%}, "
        f"{summary['top_decile_month_to_month_share']:.0%} on month-to-month contracts.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
