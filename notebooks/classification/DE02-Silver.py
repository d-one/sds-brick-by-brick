# Databricks notebook source
# MAGIC %md
# MAGIC # Read a table from Unity Catalog
# MAGIC
# MAGIC In this notebook we will do some data cleaning.

# COMMAND ----------

# set up the below params
user_email = spark.sql('select current_user() as user').collect()[0]['user']
catalog_name = user_email.split('@')[0].replace(".", "_").replace("-", "_")

# COMMAND ----------

df_bronze = spark.table(f"{catalog_name}.bronze.churn_modelling")
display(df_bronze)

# COMMAND ----------

df_bronze.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC # Clean & Augment the data

# COMMAND ----------

import pyspark.sql.functions as f
from pyspark.sql.types import StringType, DateType, FloatType, IntegerType

df_churn_bronze = spark.table(f"{catalog_name}.bronze.churn_modelling")

df_churn_silver = (
    df_bronze.withColumn("Balance", df_bronze["Balance"].cast(FloatType()))
    .withColumn("EstimatedSalary", df_bronze["EstimatedSalary"].cast(FloatType()))
    .withColumn("CustomerId", df_bronze["CustomerId"].cast(IntegerType()))
    .withColumn("Gender_Male", f.when(df_bronze["Gender"] == 'Male', 1).otherwise(0))
    .withColumnRenamed("Gender", "Gender_obj")
)

df_churn_silver.limit(5).display()

# COMMAND ----------

df_churn_silver.printSchema()

# COMMAND ----------

# MAGIC %md 
# MAGIC # Writing the dataframe to Unity Catalog

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Your Silver Schema
# MAGIC

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.silver")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Save the dataframe as a delta table inside the unity catalog

# COMMAND ----------

schema_name = "silver"
table_name = "churn_modelling"

df_churn_silver.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{catalog_name}.{schema_name}.{table_name}")


# COMMAND ----------

display(spark.table(f"{catalog_name}.{schema_name}.{table_name}").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Exit notebook when running as a workflow task

# COMMAND ----------

dbutils.notebook.exit("End of notebook when running as a workflow task")

# COMMAND ----------

# MAGIC %md
# MAGIC # Excercise
# MAGIC What happens if you need to change the schema of a silver dataframe and want to append or overwrite it to the target silver table? 
# MAGIC * Check out the option [`mergeSchema`](https://www.databricks.com/blog/2019/09/24/diving-into-delta-lake-schema-enforcement-evolution.html)
# MAGIC
# MAGIC Lets change one column name and see how the write behaves

# COMMAND ----------

# MAGIC %md
# MAGIC First lets create the a new table where we add `_testmerge` at the end of the table name

# COMMAND ----------

schema_name = "silver"
table_name = "churn_modelling"

df_churn_silver.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{catalog_name}.{schema_name}.{table_name}_testmerge")


# COMMAND ----------

# MAGIC %md
# MAGIC Lets change one of the column names

# COMMAND ----------

df_churn_silver_mergeSchema = (
    df_churn_silver.withColumnRenamed("Gender_obj", "Gender")
)

# COMMAND ----------

# MAGIC %md
# MAGIC Lets try to overwrite the table Without mergeSchema, you have to run this before the next command to get the error, why is that?

# COMMAND ----------



# COMMAND ----------

# MAGIC %md
# MAGIC With mergeSchema

# COMMAND ----------



# COMMAND ----------


