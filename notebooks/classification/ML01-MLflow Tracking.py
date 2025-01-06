# Databricks notebook source
# MAGIC  %md-sandbox
# MAGIC
# MAGIC <div style="text-align: left; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://s3.eu-central-1.amazonaws.com/co.lever.eu.client-logos/c2f22a4d-adbd-49a9-a9ca-c24c0bd5dc1a-1607101144408.png" alt="D ONE" style="width: 300px">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 400px">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC # MLflow
# MAGIC
# MAGIC <a href="https://mlflow.org/docs/latest/" target="_blank">MLflow</a> seeks to address these three core issues:
# MAGIC
# MAGIC * It’s difficult to keep track of experiments
# MAGIC * It’s difficult to reproduce code
# MAGIC * There’s no standard way to package and deploy models
# MAGIC
# MAGIC In the past, when examining a problem, you would have to manually keep track of the many models you created, as well as their associated parameters and metrics. This can quickly become tedious and take up valuable time, which is where MLflow comes in.
# MAGIC
# MAGIC MLflow is pre-installed on the Databricks Runtime for ML.

# COMMAND ----------

# MAGIC %md <i18n value="b7c8a0e0-649e-4814-8310-ae6225a57489"/>
# MAGIC
# MAGIC <div><img src="https://files.training.databricks.com/images/eLearning/ML-Part-4/mlflow-tracking.png" style="height: 300px; margin: 20px"/></div>

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ### MLflow Tracking
# MAGIC
# MAGIC MLflow Tracking is a logging API specific for machine learning and agnostic to libraries and environments that do the training.  It is organized around the concept of **runs**, which are executions of data science code.  Runs are aggregated into **experiments** where many runs can be a part of a given experiment and an MLflow server can host many experiments.
# MAGIC
# MAGIC You can use <a href="https://mlflow.org/docs/latest/python_api/mlflow.html#mlflow.set_experiment" target="_blank">mlflow.set_experiment()</a> to set an experiment, but if you do not specify an experiment, it will automatically be scoped to this notebook.

# COMMAND ----------

# MAGIC %md 
# MAGIC ### Track Runs
# MAGIC
# MAGIC Each run can record the following information:<br><br>
# MAGIC
# MAGIC - **Parameters:** Key-value pairs of input parameters such as the number of trees in a random forest model
# MAGIC - **Metrics:** Evaluation metrics such as f1 score or Area Under the ROC Curve
# MAGIC - **Artifacts:** Arbitrary output files in any format.  This can include images, pickled models, and data files
# MAGIC - **Source:** The code that originally ran the experiment
# MAGIC
# MAGIC **NOTE**: For Spark models, MLflow can only log PipelineModels.

# COMMAND ----------

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, f1_score, roc_curve
from sklearn.model_selection import train_test_split

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Let's start by loading in our dataset.

# COMMAND ----------

# user parameters
user_email = spark.sql('select current_user() as user').collect()[0]['user']
catalog_name = user_email.split('@')[0].replace(".", "_").replace("-", "_")

print(f"User Email is {user_email}")
print(f"Catalog Name is {catalog_name}")

# COMMAND ----------

schema_name = "silver"
table_name = "features"

df = spark.read.table(f"{catalog_name}.{schema_name}.{table_name}").toPandas()

# COMMAND ----------

# one-hot encode categorical columns 
#categorical data
categorical_cols = ['Geography', 'Gender', ]
# get_dummies
enriched_df = pd.get_dummies(df, columns = categorical_cols).astype(np.float64)

# train test split 
X_train, X_test, y_train, y_test = train_test_split(enriched_df.drop(["Exited"], axis=1), enriched_df[["Exited"]].values.ravel(), test_size=0.1, random_state=42)


# COMMAND ----------

# set experiment name 
experiment = mlflow.set_experiment(f"/Users/{user_email}/mlflow_experiment")

# COMMAND ----------

with mlflow.start_run(run_name="LR-Categorical-Features") as run:
    # Define pipeline
    lr = LogisticRegression()
    features = [
        'Geography_France', 'Geography_Germany', 'Geography_Spain',
        'Gender_Female', 'Gender_Male'
    ]
    model = lr.fit(X_train[features], y_train)

    # Log parameters
    mlflow.log_param("features", features)

    # Log model
    mlflow.sklearn.log_model(model, "model", input_example=X_train[features].head(5)) 

    # Evaluate predictions
    pred_proba = model.predict_proba(X_test[features])
    auc = roc_auc_score(y_test, pred_proba[:, 1])

    # Log metrics
    mlflow.log_metric("auc", auc)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC There, all done! Let's go through the other two logistic regression models and then compare our runs. 
# MAGIC
# MAGIC Next let's build our logistic regression model but use all of our features.

# COMMAND ----------

with mlflow.start_run(run_name="LR-All-Features") as run:
    # Define pipeline
    lr = LogisticRegression()
    model = lr.fit(X_train, y_train)

    # Log parameters
    mlflow.log_param("features", "all_features")

    # Log model
    mlflow.sklearn.log_model(model, "model", input_example=X_train.head(5)) 

    # Evaluate predictions
    pred_proba = model.predict_proba(X_test)
    pred = model.predict(X_test)

    auc = roc_auc_score(y_test, pred_proba[:, 1])
    f1_score_all_feat = f1_score(y_test, pred)

    # Log metrics
    mlflow.log_metric("auc", auc)
    mlflow.log_metric("f1_score", f1_score_all_feat)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Finally, we will use Logistic Regression on scaled features to predict the target variable 
# MAGIC
# MAGIC We'll also practice logging artifacts to keep a visual of the receiver operating characteristic curve.

# COMMAND ----------

import matplotlib.pyplot as plt

with mlflow.start_run(run_name="LR-Scaled-Features") as run:
    lr = LogisticRegression()
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = lr.fit(X_train_scaled, y_train)

    # Log parameters
    mlflow.log_param("features", "all_features_scaled")

    # Log model
    mlflow.sklearn.log_model(model, "model", input_example=X_train.head(5)) 

    # Evaluate predictions
    pred_proba = model.predict_proba(X_test_scaled)
    pred = model.predict(X_test_scaled)

    auc = roc_auc_score(y_test, pred_proba[:, 1])
    fpr, tpr, _ = roc_curve(y_test,  pred_proba[:, 1])
    f1_score_scaled_feat = f1_score(y_test, pred)

    # Log metrics
    mlflow.log_metric("auc", auc)
    mlflow.log_metric("f1_score", f1_score_scaled_feat)

    # Log artifact
    plt.plot(fpr,tpr,label="data 1, auc="+str(auc))
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.savefig("roc.png")

    mlflow.log_artifact("roc.png")
    plt.show()

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC That's it! Now, let's use MLflow to easily look over our work and compare model performance. You can either query past runs programmatically or use the MLflow UI.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ### Querying Past Runs
# MAGIC
# MAGIC You can query past runs programmatically in order to use this data back in Python.  The pathway to doing this is an **`MlflowClient`** object.

# COMMAND ----------

from mlflow.tracking import MlflowClient

client = MlflowClient()

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC You can also use <a href="https://www.mlflow.org/docs/1.24.0/search-syntax.html" target="_blank">search_runs</a> to find all runs for a given experiment.

# COMMAND ----------

experiment_id = run.info.experiment_id
runs_df = mlflow.search_runs(experiment_id)

display(runs_df)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Pull the last run and look at metrics.

# COMMAND ----------

runs = client.search_runs(experiment_id, order_by=["attributes.start_time desc"], max_results=1)
runs[0].data.metrics

# COMMAND ----------

runs[0].info.run_id

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Examine the results in the UI.  Look for the following:<br><br>
# MAGIC
# MAGIC 1. The **`Experiment ID`**
# MAGIC 2. The artifact location.  This is where the artifacts are stored in DBFS.
# MAGIC 3. The time the run was executed.  **Click this to see more information on the run.**
# MAGIC 4. The code that executed the run.
# MAGIC
# MAGIC
# MAGIC After clicking on the time of the run, take a look at the following:<br><br>
# MAGIC
# MAGIC 1. The Run ID will match what we printed above
# MAGIC 2. The model that we saved, included a pickled version of the model as well as the Conda environment and the **`MLmodel`** file.
# MAGIC
# MAGIC Note that you can add notes under the "Notes" tab to help keep track of important information about your models. 
# MAGIC
# MAGIC Also, click on the run for the log normal distribution and see that the histogram is saved in "Artifacts".

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ### Load Saved Model
# MAGIC
# MAGIC Let's practice <a href="https://www.mlflow.org/docs/latest/python_api/mlflow.spark.html" target="_blank">loading</a> our logged log-normal model.

# COMMAND ----------

model_path = f"runs:/{run.info.run_id}/model"
loaded_model = mlflow.sklearn.load_model(model_path)

display(loaded_model.predict(X_test))

# COMMAND ----------


