"""Feast definitions. The offline source is the dbt point-in-time feature table, exported to Parquet with
event_timestamp = snapshot_month (the moment the row's features become known: they use months before it).
A ttl of 35 days means a lookup never serves features more than one snapshot old."""
from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Bool, Float64, Int64, String

customer = Entity(name="customer", join_keys=["customer_id"], description="A telecom subscriber (IBM Telco customerID).")

source = FileSource(
    name="customer_month_features_source",
    path="../data/feast/customer_month_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

BEHAVIOUR = [
    Field(name="tenure_months", dtype=Int64),
    Field(name="total_charges_to_date", dtype=Float64),
    Field(name="charge_last_month", dtype=Float64),
    Field(name="charge_avg_6m", dtype=Float64),
    Field(name="charge_change_vs_6m", dtype=Float64),
    Field(name="data_gb_avg_3m", dtype=Float64),
    Field(name="data_gb_trend", dtype=Float64),
    Field(name="voice_minutes_avg_3m", dtype=Float64),
    Field(name="voice_minutes_trend", dtype=Float64),
    Field(name="support_tickets_3m", dtype=Int64),
    Field(name="days_late_3m", dtype=Int64),
]
PROFILE = [
    Field(name=n, dtype=Bool) for n in [
        "is_senior", "has_partner", "has_dependents", "has_phone", "has_multiple_lines", "has_online_security",
        "has_online_backup", "has_device_protection", "has_tech_support", "has_streaming_tv", "has_streaming_movies",
        "is_paperless"]
] + [Field(name="internet_service", dtype=String), Field(name="contract", dtype=String),
     Field(name="payment_method", dtype=String)]

customer_behaviour = FeatureView(
    name="customer_behaviour",
    entities=[customer],
    ttl=timedelta(days=35),
    schema=BEHAVIOUR,
    source=source,
    online=True,
    tags={"owner": "data-engineering", "point_in_time": "months before event_timestamp"},
)

customer_profile = FeatureView(
    name="customer_profile",
    entities=[customer],
    ttl=timedelta(days=35),
    schema=PROFILE,
    source=source,
    online=True,
    tags={"owner": "data-engineering", "as_of": "IBM snapshot; assumed constant"},
)
