from datetime import datetime
from airflow.decorators import dag
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

@dag(
    schedule=None,
    start_date=datetime(2025, 4, 24),  # REQUIRED
    catchup=False,
    tags=["spark"]
)
def my_dag():
    read_data = SparkSubmitOperator(
        task_id="read_Data",
        application="./include/scripts/read.py",
        conn_id="my_spark_conn",
        verbose=True
    )

    # Optional, but clearer
    read_data


dag = my_dag()
