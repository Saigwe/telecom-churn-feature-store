"""Shared feature lists, the Feast store and the scikit-learn pipeline."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FEATURE_REPO = ROOT / "feature_repo"

REAL_NUMERIC = ["tenure_months", "total_charges_to_date", "charge_last_month", "charge_avg_6m", "charge_change_vs_6m"]
SYNTHETIC_NUMERIC = ["data_gb_avg_3m", "data_gb_trend", "voice_minutes_avg_3m", "voice_minutes_trend",
                     "support_tickets_3m", "days_late_3m"]
FLAGS = ["is_senior", "has_partner", "has_dependents", "has_phone", "has_multiple_lines", "has_online_security",
         "has_online_backup", "has_device_protection", "has_tech_support", "has_streaming_tv", "has_streaming_movies",
         "is_paperless"]
CATEGORICAL = ["internet_service", "contract", "payment_method"]

FEAST_FEATURES = [f"customer_behaviour:{c}" for c in REAL_NUMERIC + SYNTHETIC_NUMERIC] + \
                 [f"customer_profile:{c}" for c in FLAGS + CATEGORICAL]

# Training data is "known" on this date: only snapshots whose 3-month label window has closed may be used,
# and the test snapshots come after a gap, as they would for a model trained then and used later.
TRAIN_SNAPSHOTS = ("2025-01-01", "2025-05-01")
TEST_SNAPSHOTS = ("2025-08-01", "2025-10-01")
SCORING_SNAPSHOT = "2026-01-01"
MODEL_NAME = "telecom_churn"
# MLflow 3 stores scikit-learn models with skops, which refuses types it can't vouch for. These two come from our
# own pipeline (the encoder's dtype setting and the boosted trees), and we only ever load models we trained.
SKOPS_TRUSTED_TYPES = ["numpy.dtype", "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor"]


def store():
    from feast import FeatureStore

    return FeatureStore(repo_path=str(FEATURE_REPO))


def tracking_uri() -> str:
    return f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}"


def pipeline(numeric: list[str], estimator):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("flags", "passthrough", FLAGS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return Pipeline([("prep", prep), ("model", estimator)])
