import sys
import base64
import pickle
import os
from datetime import datetime
from pyspark.sql.functions import lit, col, date_format

# Add folder pludgins/functions and import
paths = os.path.dirname(os.path.abspath(__file__)).split('/')
index_path = paths.index('dag_config')
sys.path.append(f"{'/'.join(paths[0:index_path])}/plugins")
from functions import general as gnrl


def main(execution_date, airflow_connection, airflow_variable):
    # Incremental method
    execution_date = datetime.strptime(execution_date, '%Y-%m-%d %H:%M:%S').date()
    execution_date = execution_date.strftime('%Y-%m-%d')

    source = "s3a://sample-bucket/encounters.csv"
    destination = 'medalion.db.brz_encounters'

    # Initial Spark Iceberg
    spark = gnrl.connect_to_spark_iceberg(
        airflow_connection['spark_connect'])

    # Load data CSV file from MiNIO
    spark_df = spark.read.option("header", "true").csv(source)

    # Filter only where start and stop are equal to execution_date.
    spark_df = spark_df.filter(
        (date_format(col("start"), 'yyyy-MM-dd') == execution_date) |
        (date_format(col("stop"), 'yyyy-MM-dd') == execution_date)
    )
    spark_df = spark_df.withColumn("partition_date", lit(execution_date))

    # Saved data overwrite to Iceberg table
    spark_df.write.format("iceberg") \
        .mode("overwrite") \
        .option("partitionOverwriteMode", "dynamic") \
        .partitionBy("partition_date") \
        .saveAsTable(destination)


if __name__ == '__main__':
    execution_date = sys.argv[1].replace('T', ' ')
    airflow_connection = pickle.loads(base64.b64decode(sys.argv[2]))
    airflow_variable = pickle.loads(base64.b64decode(sys.argv[3]))

    main(execution_date, airflow_connection, airflow_variable)
