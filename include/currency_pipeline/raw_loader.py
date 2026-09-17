"""Append raw API rows into PostgreSQL. No transformation happens here, dbt owns that."""

import json
import logging
import os

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

CREATE_SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS raw"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw.frankfurter_rates (
    raw_id          BIGSERIAL PRIMARY KEY,
    rate_date       DATE           NOT NULL,
    base_currency   CHAR(3)        NOT NULL,
    quote_currency  CHAR(3)        NOT NULL,
    rate            NUMERIC(20, 8) NOT NULL,
    provider        TEXT           NOT NULL,
    payload         JSONB          NOT NULL,
    requested_from  DATE           NOT NULL,
    requested_to    DATE           NOT NULL,
    airflow_run_id  TEXT,
    loaded_at       TIMESTAMPTZ    NOT NULL DEFAULT now()
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_frankfurter_rates_natural_key
    ON raw.frankfurter_rates (rate_date, base_currency, quote_currency, loaded_at DESC)
"""

LATEST_DATE_SQL = "SELECT max(rate_date) FROM raw.frankfurter_rates"

INSERT_SQL = """
INSERT INTO raw.frankfurter_rates (
    rate_date, base_currency, quote_currency, rate, provider,
    payload, requested_from, requested_to, airflow_run_id
) VALUES %s
"""


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        dbname=os.environ["DB_NAME"],
    )


def ensure_raw_table(cursor):
    cursor.execute(CREATE_SCHEMA_SQL)
    cursor.execute(CREATE_TABLE_SQL)
    cursor.execute(CREATE_INDEX_SQL)


def get_latest_rate_date():
    """Return the newest rate_date in the raw table, or None when it is empty."""
    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                ensure_raw_table(cursor)
                cursor.execute(LATEST_DATE_SQL)
                result = cursor.fetchone()
    finally:
        connection.close()

    return result[0]


def build_records(rows, provider, requested_from, requested_to, run_id):
    records = []
    for row in rows:
        record = (
            row["date"],
            row["base"],
            row["quote"],
            str(row["rate"]),
            provider,
            json.dumps(row),
            requested_from,
            requested_to,
            run_id,
        )
        records.append(record)
    return records


def load_raw_rates(rows, provider, requested_from, requested_to, run_id=None):
    """Append rows to raw.frankfurter_rates in a single transaction. Returns rows inserted."""
    records = build_records(rows, provider, requested_from, requested_to, run_id)

    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                ensure_raw_table(cursor)
                if records:
                    execute_values(cursor, INSERT_SQL, records)
    finally:
        connection.close()

    logger.info("Inserted %s rows into raw.frankfurter_rates", len(records))
    return len(records)