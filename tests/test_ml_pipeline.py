"""Checks on a finished run (`make all` or `make fixture-all`): training-serving consistency, the registry, scores
and the drift control. They read the artifacts the pipeline wrote, so they run after it."""
from __future__ import annotations

import json
import os
import pathlib
import sys

import duckdb
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
DB = pathlib.Path(os.environ.get("CHURN_DB", ROOT / "warehouse" / "churn.duckdb"))
RESULTS = ROOT / "results"


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text())


def test_feast_point_in_time_join_reproduces_dbt_features():
    assert load("model_comparison.json")["feast_vs_dbt_mismatches"] == 0


def test_online_store_serves_what_training_saw():
    assert load("scoring.json")["online_vs_offline_mismatches"] == 0


def test_every_active_customer_is_scored_with_a_probability():
    with duckdb.connect(str(DB), read_only=True) as con:
        scored, bad = con.execute("select count(*), count(*) filter (where churn_probability not between 0 and 1) "
                                  "from gold.churn_scores").fetchone()
        active = con.execute("select count(*) from gold.fct_customer_month_features where snapshot_month = date '2026-01-01'").fetchone()[0]
    assert scored == active > 0 and bad == 0


def test_champion_is_registered_and_never_the_leaky_model():
    import mlflow
    from common import MODEL_NAME, tracking_uri

    mlflow.set_tracking_uri(tracking_uri())
    client = mlflow.MlflowClient()
    champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    run = client.get_run(champion.run_id)
    assert run.data.params["leaky"] == "False"
    assert load("model_comparison.json")["champion"] != "hgb_leaky"


def test_drift_control_split_shows_no_drift():
    assert sum(v > 0.1 for v in load("drift.json")["control"].values()) == 0


@pytest.mark.parametrize("name", ["model_comparison.md", "scoring.md", "drift.md", "drift_report.html"])
def test_reports_written(name):
    assert (RESULTS / name).stat().st_size > 0
