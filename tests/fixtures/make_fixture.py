"""A synthetic CSV with the IBM Telco Customer Churn columns, so CI runs the real loader, dbt, Feast, MLflow
and the drift report without downloading anything. Churn depends on contract and tenure, as in the real file.

Usage: python tests/fixtures/make_fixture.py --out data/fixture/Telco-Customer-Churn.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

N = 1_200


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/fixture/Telco-Customer-Churn.csv"))
    args = ap.parse_args()
    rng = np.random.default_rng(15)
    contract = rng.choice(["Month-to-month", "One year", "Two year"], N, p=[0.55, 0.21, 0.24])
    tenure = np.where(contract == "Month-to-month", rng.integers(0, 40, N), rng.integers(1, 73, N))
    internet = rng.choice(["DSL", "Fiber optic", "No"], N, p=[0.34, 0.44, 0.22])
    monthly = np.round(np.where(internet == "Fiber optic", 85, np.where(internet == "DSL", 55, 22)) + rng.normal(0, 8, N), 2)
    p_churn = np.where(contract == "Month-to-month", 0.42, np.where(contract == "One year", 0.11, 0.03)) * np.where(tenure < 12, 1.4, 0.8)
    churn = rng.random(N) < np.clip(p_churn, 0, 0.95)
    yn = lambda p: rng.choice(["Yes", "No"], N, p=[p, 1 - p])
    df = pd.DataFrame({
        "customerID": [f"{i:04d}-FIXTR" for i in range(N)], "gender": rng.choice(["Female", "Male"], N),
        "SeniorCitizen": rng.choice(["0", "1"], N, p=[0.84, 0.16]), "Partner": yn(0.48), "Dependents": yn(0.3),
        "tenure": tenure.astype(str), "PhoneService": yn(0.9), "MultipleLines": yn(0.42), "InternetService": internet,
        "OnlineSecurity": yn(0.29), "OnlineBackup": yn(0.34), "DeviceProtection": yn(0.34), "TechSupport": yn(0.29),
        "StreamingTV": yn(0.38), "StreamingMovies": yn(0.39), "Contract": contract, "PaperlessBilling": yn(0.59),
        "PaymentMethod": rng.choice(["Electronic check", "Mailed check", "Bank transfer (automatic)",
                                     "Credit card (automatic)"], N),
        "MonthlyCharges": monthly.astype(str),
        "TotalCharges": np.where(tenure == 0, " ", np.round(monthly * tenure * rng.uniform(0.9, 1.0, N), 2).astype(str)),
        "Churn": np.where(churn, "Yes", "No"),
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {N:,} synthetic Telco-format customers to {args.out}")


if __name__ == "__main__":
    main()
