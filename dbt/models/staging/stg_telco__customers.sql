-- One row per customer from the IBM snapshot. Contract and services are known only as of the snapshot and are
-- treated as unchanged over the customer's life (the file has no history). The extract-time columns
-- (tenure, MonthlyCharges, TotalCharges) are kept with an `extract_` prefix and must NOT be used as features for
-- earlier snapshots: they describe December 2025, not the past. The point-in-time versions come from usage.
select
    customerID                                                      as customer_id,
    gender,
    SeniorCitizen = '1'                                             as is_senior,
    Partner = 'Yes'                                                 as has_partner,
    Dependents = 'Yes'                                              as has_dependents,
    PhoneService = 'Yes'                                            as has_phone,
    MultipleLines = 'Yes'                                           as has_multiple_lines,
    InternetService                                                 as internet_service,
    OnlineSecurity = 'Yes'                                          as has_online_security,
    OnlineBackup = 'Yes'                                            as has_online_backup,
    DeviceProtection = 'Yes'                                        as has_device_protection,
    TechSupport = 'Yes'                                             as has_tech_support,
    StreamingTV = 'Yes'                                             as has_streaming_tv,
    StreamingMovies = 'Yes'                                         as has_streaming_movies,
    Contract                                                        as contract,
    PaperlessBilling = 'Yes'                                        as is_paperless,
    PaymentMethod                                                   as payment_method,
    cast(tenure as integer)                                         as extract_tenure_months,
    cast(MonthlyCharges as double)                                  as extract_monthly_charges,
    try_cast(nullif(trim(TotalCharges), '') as double)              as extract_total_charges,
    Churn = 'Yes'                                                   as churned_by_extract
from {{ source('bronze', 'telco_customers') }}
