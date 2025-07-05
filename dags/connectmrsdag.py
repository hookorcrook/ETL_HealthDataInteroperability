from datetime import datetime
from airflow.decorators import dag
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

@dag(
    schedule=None,
    start_date=datetime(2025, 4, 24),  # REQUIRED
    catchup=False,
    tags=["spark"]
)
def connect_mrs_dag():
    connect_mrs = SparkSubmitOperator(
        task_id="connect_mrs",
        application="./include/scripts/connect-openmrs.py",
        conn_id="my_spark_conn",
        verbose=True
    )

    # Optional, but clearer
    connect_mrs


dag = connect_mrs_dag()
