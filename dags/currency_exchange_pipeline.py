"""
Daily currency exchange ELT pipeline.

1. extract_load_raw   Fetch rates from Frankfurter and append them to raw.frankfurter_rates.
                      Loads full history on the first run, then a rolling lookback window.
2. dbt_deps           Install dbt packages
3. dbt_source_freshness  Stop if the raw data is stale
4. dbt_build          Run and test all models, including the moving average forecast
5. dbt_docs_generate  Refresh dbt docs and lineage
"""

import logging
import os
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from currency_pipeline.date_range import resolve_date_range
from currency_pipeline.frankfurter_client import fetch_rates
from currency_pipeline.raw_loader import get_latest_rate_date, load_raw_rates

logger = logging.getLogger(__name__)

BASE_CURRENCY = os.environ.get("BASE_CURRENCY", "USD")
QUOTE_CURRENCIES = os.environ.get("QUOTE_CURRENCIES", "IDR,MYR,SGD").split(",")
RATE_PROVIDER = os.environ.get("RATE_PROVIDER", "ECB")

# Re-fetch the last few days on every run so late or revised rates are picked up.
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))

# First date to load when the raw table is empty.
HISTORY_START_DATE = os.environ.get("HISTORY_START_DATE", "2020-01-01")

DBT_BIN = "/home/airflow/dbt_venv/bin/dbt"
DBT_DIR = "/opt/airflow/dbt"
DBT_FLAGS = f"--project-dir {DBT_DIR} --profiles-dir {DBT_DIR}"


def extract_load_raw(**context):
    params = context["params"]
    latest_loaded_date = get_latest_rate_date()

    if latest_loaded_date is None:
        logger.info("Raw table is empty, loading history from %s", HISTORY_START_DATE)
    else:
        logger.info("Latest loaded rate_date is %s", latest_loaded_date)

    start_date, end_date = resolve_date_range(
        end_date=context["data_interval_end"].date(),
        lookback_days=LOOKBACK_DAYS,
        history_start_date=HISTORY_START_DATE,
        latest_loaded_date=latest_loaded_date,
        start_override=params.get("start_date"),
        end_override=params.get("end_date"),
    )

    rows = fetch_rates(
        start_date=start_date,
        end_date=end_date,
        base_currency=BASE_CURRENCY,
        quote_currencies=QUOTE_CURRENCIES,
        provider=RATE_PROVIDER,
    )

    if not rows:
        logger.warning("No rates published between %s and %s", start_date, end_date)

    inserted = load_raw_rates(
        rows=rows,
        provider=RATE_PROVIDER,
        requested_from=start_date,
        requested_to=end_date,
        run_id=context["run_id"],
    )
    # Only a small count goes to XCom, never the data itself.
    return inserted


default_args = {
    "owner": "patra",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="currency_exchange_pipeline",
    description="Frankfurter rates to PostgreSQL, modeled with dbt",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    # ECB publishes around 16:00 CET on working days.
    schedule="0 17 * * 1-5",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["currency", "dbt", "elt"],
    params={
        "start_date": Param(
            None,
            type=["null", "string"],
            description="Optional manual start date (YYYY-MM-DD). Leave empty for automatic behaviour.",
        ),
        "end_date": Param(
            None,
            type=["null", "string"],
            description="Optional manual end date (YYYY-MM-DD). Defaults to the run date.",
        ),
    },
) as dag:
    extract_load_task = PythonOperator(
        task_id="extract_load_raw",
        python_callable=extract_load_raw,
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_BIN} deps {DBT_FLAGS}",
    )

    dbt_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT_BIN} source freshness {DBT_FLAGS}",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build {DBT_FLAGS}",
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"{DBT_BIN} docs generate {DBT_FLAGS}",
    )

    extract_load_task >> dbt_deps >> dbt_source_freshness >> dbt_build >> dbt_docs_generate