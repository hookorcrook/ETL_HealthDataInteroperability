from pyspark.sql import SparkSession
import os

def main():
    spark = SparkSession.builder \
        .appName("PySpark Example") \
        .getOrCreate()

    p = os.path.join(os.path.curdir,"/opt/airflow/include/data.csv")
    #df = spark.read.csv("./opt/airflow/include/data.csv", header="true") # /usr/local/airflow/include/data.csv that path must exist in your Spark containers
    # df = spark.read.csv(p, header="true") # /usr/local/airflow/include/data.csv that path must exist in your Spark containers

    df = spark.read.csv("/opt/airflow/include/data.csv", header=True, inferSchema=True)
    df.show()
    
    spark.stop()

if __name__ == "__main__":
    main()