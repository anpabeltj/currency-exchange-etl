import sys
sys.path.insert(0, '/opt/airflow/scripts')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

import extract as e
import transform as t
import load as l

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
}


with DAG('currency_exchange_pipeline', default_args=default_args, schedule='@daily', catchup=False) as dag:
    def run_extract():
        return e.extract_currency()

    def run_transform(**context):
        data = context['ti'].xcom_pull(task_ids='extract_currency_exchange')
        return t.transform_currency(data)

    def run_load(**context):
        data = context['ti'].xcom_pull(task_ids='transform_currency_exchange')
        return l.load(data)

    extract_task = PythonOperator(
        task_id='extract_currency_exchange',
        python_callable=run_extract
    )

    transform_task = PythonOperator(
        task_id='transform_currency_exchange',
        python_callable=run_transform
    )

    load_task = PythonOperator(
        task_id='load_currency_exchange',
        python_callable=run_load
    )

    extract_task >> transform_task >> load_task