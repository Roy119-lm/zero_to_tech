from insert import insert
from pyspark.sql import SparkSession
import pandas as pd

spark = SparkSession.builder \
    .appName("IcebergExample") \
    .getOrCreate()

file_path = '/opt/spark/data/“高效办成一件事”标杆场景数量.xlsx'

spark.sql('delete from indicators.data') #删除表中的所有数据

insert(file_path)
