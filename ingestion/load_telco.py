"""Load the IBM Telco Customer Churn data and derive a monthly history for it.

    bronze.telco_customers   the real file as delivered: 7,043 customers, one snapshot (text columns)
    bronze.usage_monthly     one row per customer per active month, DERIVED here with a fixed seed

The IBM file is a single snapshot, so a monthly history has to be built to train a point-in-time model:
  - Timeline: the snapshot is taken at the end of December 2025. A customer who stayed has been active for
    `tenure` months up to December 2025. A churner's last active month is drawn uniformly from December 2024 to
    November 2025 (seeded), so churn months fall evenly across 2025, and their `tenure` months end there.
  - monthly_charge_usd is REAL-derived: a straight line from a start value to today's MonthlyCharges whose sum
    equals the customer's real TotalCharges (price rises and add-ons show up as the ramp).
  - data_gb, voice_minutes, support_tickets and days_late are SYNTHETIC. They depend on the customer's real
    services and payment method, and churners' last three months drift (less data use, more tickets), so the
    usage features carry PLANTED signal. The README reports models with and without them.

Source (public, IBM's own repository):
https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/data/Telco-Customer-Churn.csv

Usage: python ingestion/load_telco.py --csv data/raw/Telco-Customer-Churn.csv --db warehouse/churn.duckdb
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

SNAPSHOT = pd.Period("2025-12", "M")
SEED = 1515


def monthly_history(t: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    tenure = t.tenure.astype(int).to_numpy()
    churned = t.Churn.eq("Yes").to_numpy()
    last = np.where(churned, rng.integers(0, 12, len(t)), 12)  # months after December 2024
    monthly = t.MonthlyCharges.astype(float).to_numpy()
    total = pd.to_numeric(t.TotalCharges.str.strip(), errors="coerce").fillna(0).to_numpy()
    fiber = t.InternetService.eq("Fiber optic").to_numpy()
    has_internet = t.InternetService.ne("No").to_numpy()
    echeck = t.PaymentMethod.eq("Electronic check").to_numpy()
    rows = []
    for i in np.flatnonzero(tenure > 0):
        n = tenure[i]
        months = pd.period_range(end=pd.Period("2024-12", "M") + int(last[i]), periods=n, freq="M")
        # charges: linear ramp ending at today's monthly charge whose sum equals the real total
        start = np.clip(2 * total[i] / n - monthly[i], 0.5 * monthly[i], 1.5 * monthly[i]) if n > 1 else monthly[i]
        charge = np.linspace(start, monthly[i], n)
        charge *= total[i] / charge.sum() if charge.sum() > 0 and total[i] > 0 else 1
        base_gb = (25 if fiber[i] else 9) * has_internet[i] * rng.lognormal(0, 0.4)
        gb = base_gb * rng.lognormal(0, 0.25, n)
        minutes = rng.gamma(4, 80, n)
        tickets = rng.poisson(0.15 + 0.15 * fiber[i], n)
        late = rng.poisson(1.5 if echeck[i] else 0.4, n)
        if churned[i]:  # planted pre-churn drift in the last three months
            k = min(3, n)
            ramp = np.linspace(0.85, 0.6, k)
            gb[-k:] *= ramp
            minutes[-k:] *= ramp
            tickets[-k:] += rng.poisson(0.5, k)
            late[-k:] += rng.poisson(1.0, k)
        rows.append(pd.DataFrame({
            "customer_id": t.customerID.iat[i], "usage_month": months.to_timestamp(),
            "monthly_charge_usd": charge.round(2), "data_gb": gb.round(2), "voice_minutes": minutes.round(0),
            "support_tickets": tickets, "days_late": late,
        }))
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=Path("data/raw/Telco-Customer-Churn.csv"))
    ap.add_argument("--db", default="warehouse/churn.duckdb")
    args = ap.parse_args()
    start = time.time()
    t = pd.read_csv(args.csv, dtype=str, keep_default_na=False)
    usage = monthly_history(t, np.random.default_rng(SEED))
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists bronze")
    con.execute("create or replace table bronze.telco_customers as select * from t")
    con.execute("create or replace table bronze.usage_monthly as select * from usage")
    churners = int(t.Churn.eq("Yes").sum())
    print(f"bronze.telco_customers {len(t):,} customers ({churners:,} churned); "
          f"bronze.usage_monthly {len(usage):,} customer-months ({time.time() - start:.1f}s)")


if __name__ == "__main__":
    main()
