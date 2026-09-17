FROM apache/airflow:2.10.5-python3.11

# dbt lives in its own virtualenv so its dependencies never clash with Airflow's
ENV DBT_VENV=/home/airflow/dbt_venv

RUN python -m venv ${DBT_VENV} \
    && ${DBT_VENV}/bin/pip install --no-cache-dir \
        "dbt-core~=1.11.0" \
        "dbt-postgres~=1.11.0"