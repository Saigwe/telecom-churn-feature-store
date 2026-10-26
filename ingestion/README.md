# Ingestion

`load_telco.py` loads the IBM Telco Customer Churn CSV into `bronze.telco_customers` as delivered, and derives
`bronze.usage_monthly`: one row per customer per active month, with a fixed seed.

- Monthly charges are a ramp to the customer's current MonthlyCharges that sums to their real TotalCharges.
- Data, minutes, support tickets and late days are synthetic, with drift planted in churners' last three months.

```bash
make download   # https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv
python ingestion/load_telco.py --csv data/raw/Telco-Customer-Churn.csv --db warehouse/churn.duckdb
```

CI uses `tests/fixtures/make_fixture.py`, which writes a synthetic CSV with the same columns.
