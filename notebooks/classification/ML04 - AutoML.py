# Databricks notebook source
# MAGIC  %md-sandbox
# MAGIC
# MAGIC <div style="text-align: left; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://s3.eu-central-1.amazonaws.com/co.lever.eu.client-logos/c2f22a4d-adbd-49a9-a9ca-c24c0bd5dc1a-1607101144408.png" alt="D ONE" style="width: 300px">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 400px">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # AutoML
# MAGIC
# MAGIC <a href="https://docs.databricks.com/applications/machine-learning/automl.html" target="_blank">Databricks AutoML</a> helps you automatically build machine learning models both through a UI and programmatically. It prepares the dataset for model training and then performs and records a set of trials (using HyperOpt), creating, tuning, and evaluating multiple models. 
# MAGIC
# MAGIC In this notebook you will:
# MAGIC  - Use AutoML to automatically train and tune your models
# MAGIC  - Run AutoML in Python and through the UI
# MAGIC  - Interpret the results of an AutoML run

# COMMAND ----------

# MAGIC %md <i18n value="7aa84cf3-1b6c-4ba4-9249-00359ee8d70a"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC Currently, AutoML uses a combination of XGBoost and sklearn (only single node models) but optimizes the hyperparameters within each.

# COMMAND ----------

# set up the below params
user_email = spark.sql('select current_user() as user').collect()[0]['user']
catalog_name = user_email.split('@')[0].replace(".", "_").replace("-", "_")

print(f"User Email is {user_email}")
print(f"Catalog Name is {catalog_name}")

# COMMAND ----------

schema_name = "silver"
table_name = "features"

df = spark.read.table(f"{catalog_name}.{schema_name}.{table_name}").toPandas()

# COMMAND ----------

from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# one-hot encode categorical columns 
#categorical data
categorical_cols = ['Geography', 'Gender', ]
# get_dummies
enriched_df = pd.get_dummies(df, columns = categorical_cols).astype(np.float64)
enriched_df['Exited'] = enriched_df['Exited'].astype('int64')

# train test split 
train_df, test_df, _, _ = train_test_split(enriched_df, enriched_df[["Exited"]].values.ravel(), test_size=0.1, random_state=42)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC We can now use AutoML to search for the optimal <a href="https://docs.databricks.com/en/machine-learning/automl/train-ml-model-automl-api.html#classification-specification" target="_blank">classification</a> model. 
# MAGIC
# MAGIC Required parameters:
# MAGIC * **`dataset`** - Input Spark or pandas DataFrame that contains training features and targets. If using a Spark DataFrame, it will convert it to a Pandas DataFrame under the hood by calling .toPandas() - just be careful you don't OOM!
# MAGIC * **`target_col`** - Column name of the target labels
# MAGIC
# MAGIC We will also specify optional parameters (https://docs.databricks.com/en/machine-learning/automl/automl-api-reference.html):
# MAGIC * **`primary_metric`** - Primary metric to select the best model. Each trial will compute several metrics, but this one determines which model is selected from all the trials. One of **`f1`** (default, f1 score), **`log_loss`** (logistic loss or cross-entropy loss), **`precision`**, **`accuracy`**, **`roc_auc`** for classification problems.
# MAGIC * **`timeout_minutes`** - The maximum time to wait for the AutoML trials to complete. **`timeout_minutes=None`** will run the trials without any timeout restrictions
# MAGIC * **`max_trials`** - The maximum number of trials to run. When **`max_trials=None`**, maximum number of trials will run to completion.

# COMMAND ----------

from databricks import automl

summary = automl.classify(train_df, target_col="Exited", primary_metric="f1", timeout_minutes=5, max_trials=10)

# COMMAND ----------

# MAGIC %md 
# MAGIC  
# MAGIC
# MAGIC After running the previous cell, you will notice two notebooks and an MLflow experiment:
# MAGIC * **`Data exploration notebook`** - we can see a Profiling Report which organizes the input columns and discusses values, frequency and other information
# MAGIC * **`Best trial notebook`** - shows the source code for reproducing the best trial conducted by AutoML
# MAGIC * **`MLflow experiment`** - contains high level information, such as the root artifact location, experiment ID, and experiment tags. The list of trials contains detailed summaries of each trial, such as the notebook and model location, training parameters, and overall metrics.
# MAGIC
# MAGIC Dig into these notebooks and the MLflow experiment - what do you find?
# MAGIC
# MAGIC Additionally, AutoML shows a short list of metrics from the best run of the model.

# COMMAND ----------

print(summary.best_trial)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC Now we can test the model that we got from AutoML against our test data. We'll be using <a href="https://mlflow.org/docs/latest/python_api/mlflow.pyfunc.html#mlflow.pyfunc.spark_udf" target="_blank">mlflow.pyfunc.spark_udf</a> to register our model as a UDF and apply it in parallel to our test data.

# COMMAND ----------

# Load the best trial as an MLflow Model
import mlflow
from pyspark.sql.types import DoubleType
import pyspark.sql.functions as f

model_uri = f"runs:/{summary.best_trial.mlflow_run_id}/model"

predict = mlflow.pyfunc.spark_udf(spark, model_uri)
test_sdf = spark.createDataFrame(test_df)
pred_sdf = test_sdf.withColumn("prediction", predict(*test_sdf.drop("Exited").columns)[0])
pred_sdf = pred_sdf.withColumn("prediction", f.col("prediction").cast(DoubleType()))
display(pred_sdf)

# COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator

classification_evaluator = BinaryClassificationEvaluator(rawPredictionCol="prediction" ,labelCol="Exited", metricName="areaUnderROC")
auc = classification_evaluator.evaluate(pred_sdf)
print(f"auc score on test dataset: {auc:.3f}")

# COMMAND ----------


