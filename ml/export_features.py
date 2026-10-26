"""Export the dbt point-in-time feature table to Parquet as Feast's offline source.

event_timestamp = snapshot_month (UTC): a row's features are known at the start of its snapshot month.

Usage: python ml/export_features.py --db warehouse/churn.duckdb --out data/feast/customer_month_features.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse/churn.duckdb")
    ap.add_argument("--out", type=Path, default=Path("data/feast/customer_month_features.parquet"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db, read_only=True)
    df = con.execute("""
        select * exclude (churned_next_3m, feature_cutoff_month),
               timezone('UTC', cast(snapshot_month as timestamp)) as event_timestamp,
               timezone('UTC', cast(snapshot_month as timestamp)) as created_timestamp
        from gold.fct_customer_month_features
    """).df()
    df.to_parquet(args.out, index=False)
    print(f"{len(df):,} feature rows -> {args.out}")


if __name__ == "__main__":
    main()
