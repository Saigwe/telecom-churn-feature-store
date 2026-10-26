"""Feature drift with Evidently: the training snapshots (reference) against the scoring snapshot (current), plus a
control run that splits the training months in half by customer, which should show little or no drift.

Writes results/drift_report.html (full Evidently report) and results/drift.md (the summary).
Usage: python ml/drift.py --db warehouse/churn.duckdb
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CATEGORICAL, FLAGS, REAL_NUMERIC, ROOT, SCORING_SNAPSHOT, SYNTHETIC_NUMERIC, TRAIN_SNAPSHOTS  # noqa: E402

COLUMNS = REAL_NUMERIC + SYNTHETIC_NUMERIC + FLAGS + CATEGORICAL


def drift(reference: pd.DataFrame, current: pd.DataFrame, html: pathlib.Path | None = None) -> dict[str, float]:
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    definition = DataDefinition(numerical_columns=REAL_NUMERIC + SYNTHETIC_NUMERIC,
                                categorical_columns=FLAGS + CATEGORICAL)
    ref = Dataset.from_pandas(reference[COLUMNS], data_definition=definition)
    cur = Dataset.from_pandas(current[COLUMNS], data_definition=definition)
    result = Report([DataDriftPreset()]).run(reference_data=ref, current_data=cur)
    if html:
        result.save_html(str(html))
    scores = {}
    for metric in result.dict()["metrics"]:
        name = metric.get("metric_name", "")
        if name.startswith("ValueDrift(column="):
            column = name.split("column=")[1].split(",")[0].rstrip(")")
            scores[column] = float(metric["value"])
    return scores


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse/churn.duckdb")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results")
    args = ap.parse_args()
    df = pd.read_parquet(ROOT / "data" / "feast" / "customer_month_features.parquet")
    df[FLAGS] = df[FLAGS].astype(int)
    month = df.snapshot_month.astype(str)
    reference = df[(month >= TRAIN_SNAPSHOTS[0]) & (month <= TRAIN_SNAPSHOTS[1])]
    current = df[month == SCORING_SNAPSHOT]
    args.out.mkdir(parents=True, exist_ok=True)
    live = drift(reference, current, args.out / "drift_report.html")
    half = pd.util.hash_pandas_object(reference.customer_id, index=False).to_numpy() % 2 == 0  # stable across runs
    control = drift(reference[half], reference[~half])

    # Evidently's default per-column test: Wasserstein distance (numeric) or Jensen-Shannon (categorical), drift at > 0.1
    drifted = sorted((c for c, v in live.items() if v > 0.1), key=lambda c: -live[c])
    lines = ["# Feature drift: training snapshots vs the scoring snapshot", "",
             f"Reference: {len(reference):,} rows (snapshots {TRAIN_SNAPSHOTS[0][:7]} to {TRAIN_SNAPSHOTS[1][:7]}). "
             f"Current: {len(current):,} rows ({SCORING_SNAPSHOT[:7]}). Full report: `drift_report.html`.", "",
             f"- Drifted columns: {len(drifted)} of {len(live)}"
             + (f" ({', '.join(drifted)})" if drifted else ""),
             f"- Control (training months split in half by customer): "
             f"{sum(v > 0.1 for v in control.values())} of {len(control)} columns drifted", "",
             "| Column | Drift score (current) | Drift score (control) |", "|---|---:|---:|"]
    lines += [f"| {c} | {live[c]:.3f} | {control.get(c, float('nan')):.3f} |" for c in sorted(live, key=lambda c: -live[c])]
    (args.out / "drift.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out / "drift.json").write_text(json.dumps({"current": live, "control": control, "drifted": drifted}, indent=1))
    print("\n".join(lines[:7]))


if __name__ == "__main__":
    main()
