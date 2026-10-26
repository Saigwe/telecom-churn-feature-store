PY ?= python
DB ?= warehouse/churn.duckdb
CSV ?= data/raw/Telco-Customer-Churn.csv
DBT_BIN ?= dbt
DBT = cd dbt && DUCKDB_PATH=../$(DB) $(DBT_BIN)
IBM = https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv

.PHONY: all download load dbt features train score drift test fixture-all clean

all: load dbt features train score drift test   ## real IBM Telco data (run `make download` once first)

download:   ## ~1 MB from IBM's public GitHub repository
	mkdir -p data/raw && curl -L -o $(CSV) $(IBM)

load:
	$(PY) ingestion/load_telco.py --csv $(CSV) --db $(DB)

dbt:
	$(DBT) build --profiles-dir .

features:   ## dbt table -> Parquet -> Feast registry
	$(PY) ml/export_features.py --db $(DB)
	cd feature_repo && $(PY) -m feast.cli.cli apply

train:      ## Feast point-in-time training set -> models tracked and registered in MLflow
	$(PY) ml/train.py --db $(DB)

score:      ## Feast online store -> champion model -> gold.churn_scores
	$(PY) ml/score.py --db $(DB)

drift:      ## Evidently: training reference vs the scoring snapshot
	$(PY) ml/drift.py --db $(DB)

test:
	CHURN_DB=$(DB) $(PY) -m pytest -q tests

fixture-all:   ## synthetic Telco-format CSV through the same pipeline (CI)
	$(PY) tests/fixtures/make_fixture.py --out data/fixture/Telco-Customer-Churn.csv
	$(MAKE) all DB=warehouse/fixture.duckdb CSV=data/fixture/Telco-Customer-Churn.csv

clean:
	rm -rf warehouse dbt/target dbt/logs data/feast data/fixture mlruns mlflow.db
