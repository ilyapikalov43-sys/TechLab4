"""
DAG для ETL-пайплайна данных о потреблении ресурсов.
Расписание: ежедневно в 08:00.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta
import sys
import os

# Добавление скриптов в путь
sys.path.insert(0, '/opt/airflow/scripts')

from extract import extract_all
from transform import transform_all
from load import load_all
from quality_checks import run_quality_checks
from drift_monitoring import run_drift_analysis

default_args = {
    'owner': 'ilya_pikalov',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'energy_consumption_etl',
    default_args=default_args,
    description='ETL пайплайн для данных о потреблении ресурсов',
    schedule_interval='0 8 * * *',  # Ежедневно в 08:00
    catchup=False,
    tags=['etl', 'energy', 'building']
)

# Операторы
start = DummyOperator(task_id='start', dag=dag)

def extract_task_func(**context):
    """Извлечение данных."""
    date = context.get('data_interval_start').date() if context.get('data_interval_start') else None
    data = extract_all(date=date)
    # Сохранение в XCom для передачи в следующую задачу
    context['task_instance'].xcom_push(key='extracted_data', value=data)
    return "Extraction completed"

extract = PythonOperator(
    task_id='extract',
    python_callable=extract_task_func,
    dag=dag
)

def transform_task_func(**context):
    """Трансформация данных."""
    ti = context['task_instance']
    extracted = ti.xcom_pull(key='extracted_data', task_ids='extract')
    transformed = transform_all(extracted)
    ti.xcom_push(key='transformed_data', value=transformed)
    return "Transformation completed"

transform = PythonOperator(
    task_id='transform',
    python_callable=transform_task_func,
    dag=dag
)

def load_task_func(**context):
    """Загрузка данных в хранилища."""
    ti = context['task_instance']
    transformed = ti.xcom_pull(key='transformed_data', task_ids='transform')
    load_all(transformed)
    return "Load completed"

load = PythonOperator(
    task_id='load',
    python_callable