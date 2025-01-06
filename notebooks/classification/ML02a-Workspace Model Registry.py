# Databricks notebook source
# MAGIC  %md-sandbox
# MAGIC
# MAGIC <div style="text-align: left; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://s3.eu-central-1.amazonaws.com/co.lever.eu.client-logos/c2f22a4d-adbd-49a9-a9ca-c24c0bd5dc1a-1607101144408.png" alt="D ONE" style="width: 300px">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 400px">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Registry
# MAGIC
# MAGIC MLflow Model Registry is a collaborative hub where teams can share ML models, work together from experimentation to online testing and production, integrate with approval and governance workflows, and monitor ML deployments and their performance.  This notebook explores how to manage models using the MLflow model registry.
# MAGIC
# MAGIC
# MAGIC In this notebook we will:
# MAGIC  - Register a model using MLflow
# MAGIC  - Manage the model lifecycle
# MAGIC  - Archive and delete models
# MAGIC

# COMMAND ----------

# MAGIC %md-sandbox <i18n value="fe857eeb-6119-4927-ad79-77eaa7bffe3a"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC ### Model Registry
# MAGIC
# MAGIC The MLflow Model Registry component is a centralized model store, set of APIs, and UI, to collaboratively manage the full lifecycle of an MLflow Model. It provides model lineage (which MLflow Experiment and Run produced the model), model versioning, stage transitions (e.g. from staging to production), annotations (e.g. with comments, tags), and deployment management (e.g. which production jobs have requested a specific model version).
# MAGIC
# MAGIC Model registry has the following features:<br><br>
# MAGIC
# MAGIC * **Central Repository:** Register MLflow models with the MLflow Model Registry. A registered model has a unique name, version, stage, and other metadata.
# MAGIC * **Model Versioning:** Automatically keep track of versions for registered models when updated.
# MAGIC * **Model Stage:** Assigned preset or custom stages to each model version, like “Staging” and “Production” to represent the lifecycle of a model.
# MAGIC * **Model Stage Transitions:** Record new registration events or changes as activities that automatically log users, changes, and additional metadata such as comments.
# MAGIC * **CI/CD Workflow Integration:** Record stage transitions, request, review and approve changes as part of CI/CD pipelines for better control and governance.
# MAGIC
# MAGIC <div><img src="https://files.training.databricks.com/images/eLearning/ML-Part-4/model-registry.png" style="height: 400px; margin: 20px"/></div>
# MAGIC
# MAGIC See <a href="https://mlflow.org/docs/latest/registry.html" target="_blank">the MLflow docs</a> for more details on the model registry.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC
# MAGIC ### Registering a Model
# MAGIC
# MAGIC The following workflow will work with either the UI or in pure Python.  This notebook will use pure Python.
# MAGIC
# MAGIC Explore the UI throughout this NOTEBOOK by clicking the "Models" tab on the left-hand side of the screen.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC
# MAGIC Train a model and log it to MLflow using <a href="https://docs.databricks.com/applications/mlflow/databricks-autologging.html" target="_blank">autologging</a>. Autologging allows you to log metrics, parameters, and models without the need for explicit log statements.
# MAGIC
# MAGIC There are a few ways to use autologging:
# MAGIC
# MAGIC   1. Call **`mlflow.autolog()`** before your training code. This will enable autologging for each supported library you have installed as soon as you import it.
# MAGIC
# MAGIC   2. Enable autologging at the workspace level from the admin console
# MAGIC
# MAGIC   3. Use library-specific autolog calls for each library you use in your code. (e.g. **`mlflow.spark.autolog()`**)
# MAGIC
# MAGIC Here we are only using numeric features for simplicity of building the random forest.

# COMMAND ----------

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

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
experiment = mlflow.set_experiment(f"/Users/{user_email}/opap_mlflow_experiment")

# COMMAND ----------

with mlflow.start_run(run_name="LR Model Autolog") as run:
    mlflow.sklearn.autolog(log_input_examples=False, log_model_signatures=True, log_models=True)
    lr = LogisticRegression()
    lr.fit(X_train, y_train)
    signature = infer_signature(X_train, lr.predict(X_train))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC Create a unique model name so you don't clash with other workspace users. 
# MAGIC
# MAGIC Note that a registered model name must be a non-empty UTF-8 string and cannot contain forward slashes(/), periods(.), or colons(:).

# COMMAND ----------

model_name = f"{catalog_name}_lr_model"
model_name

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC
# MAGIC Register the model.

# COMMAND ----------

run_id = run.info.run_id
model_uri = f"runs:/{run_id}/model"

model_details = mlflow.register_model(model_uri=model_uri, name=model_name)

# COMMAND ----------

# MAGIC %md-sandbox <i18n value="fe857eeb-6119-4927-ad79-77eaa7bffe3a"/>
# MAGIC
# MAGIC
# MAGIC  **Open the *Models* tab on the left of the screen to explore the registered model.**  Note the following:<br><br>
# MAGIC
# MAGIC * It logged who trained the model and what code was used
# MAGIC * It logged a history of actions taken on this model
# MAGIC * It logged this model as a first version
# MAGIC
# MAGIC <div><img src="https://files.training.databricks.com/images/301/registered_model_new.png" style="height: 600px; margin: 20px"/></div>

# COMMAND ----------

# MAGIC %md <i18n value="481cba23-661f-4de7-a1d8-06b6be8c57d3"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC Check the status.

# COMMAND ----------

from mlflow.tracking.client import MlflowClient

client = MlflowClient()
model_version_details = client.get_model_version(name=model_name, version=1)

model_version_details.status

# COMMAND ----------

# MAGIC %md <i18n value="10556266-2903-4afc-8af9-3213d244aa21"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC Now add a model description

# COMMAND ----------

client.update_registered_model(
    name=model_details.name,
    description="This model forecasts customers' excitement based on various features."
)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Add a version-specific description.

# COMMAND ----------

client.update_model_version(
    name=model_details.name,
    version=model_details.version,
    description="This model version was built using logistic regression with sklearn."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Deploying a Model
# MAGIC
# MAGIC The MLflow Model Registry defines several model stages: **`None`**, **`Staging`**, **`Production`**, and **`Archived`**. Each stage has a unique meaning. For example, **`Staging`** is meant for model testing, while **`Production`** is for models that have completed the testing or review processes and have been deployed to applications. 
# MAGIC
# MAGIC Users with appropriate permissions can transition models between stages.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC
# MAGIC Now that you've learned about stage transitions, transition the model to the **`Production`** stage.

# COMMAND ----------

import time

time.sleep(10) # In case the registration is still pending

# COMMAND ----------

client.transition_model_version_stage(
    name=model_details.name,
    version=model_details.version,
    stage="Production"
)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Fetch the model's current status.

# COMMAND ----------

model_version_details = client.get_model_version(
    name=model_details.name,
    version=model_details.version
)
print(f"The current model stage is: '{model_version_details.current_stage}'")

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Fetch the latest model using a **`pyfunc`**.  Loading the model in this way allows us to use the model regardless of the package that was used to train it.
# MAGIC
# MAGIC NOTE!! You can load a specific version of the model too.

# COMMAND ----------

import mlflow.pyfunc

model_version_uri = f"models:/{model_name}/1"

print(f"Loading registered model version from URI: '{model_version_uri}'")
model_version_1 = mlflow.pyfunc.load_model(model_version_uri)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Apply the model.

# COMMAND ----------

model_version_1.predict(X_test)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ### Deploying a New Model Version
# MAGIC
# MAGIC The MLflow Model Registry enables you to create multiple model versions corresponding to a single registered model. By performing stage transitions, you can seamlessly integrate new model versions into your staging or production environments.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Create a new model version and register that model when it's logged.

# COMMAND ----------

from sklearn.linear_model import RidgeClassifier

with mlflow.start_run(run_name="LR Ridge Model") as run:
    alpha = .9
    ridge_classifier = RidgeClassifier(alpha=alpha)
    ridge_classifier.fit(X_train, y_train)

    # Specify the `registered_model_name` parameter of the `mlflow.sklearn.log_model()`
    # function to register the model with the MLflow Model Registry. This automatically
    # creates a new model version

    mlflow.sklearn.log_model(
        sk_model=ridge_classifier,
        artifact_path="sklearn-ridge-model",
        registered_model_name=model_name,
    )

    mlflow.log_params(ridge_classifier.get_params())
    mlflow.log_metric("f1_score_ridge", f1_score(y_test, ridge_classifier.predict(X_test)))

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Put the new model into staging.

# COMMAND ----------

import time

time.sleep(10)

client.transition_model_version_stage(
    name=model_details.name,
    version=2,
    stage="Staging"
)

# COMMAND ----------

# MAGIC %md-sandbox <i18n value="fe857eeb-6119-4927-ad79-77eaa7bffe3a"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC Check the UI to see the new model version.
# MAGIC
# MAGIC <div><img src="https://files.training.databricks.com/images/301/model_version_new.png" style="height: 600px; margin: 20px"/></div>

# COMMAND ----------

# MAGIC %md 
# MAGIC Use the search functionality to grab the latest model version.

# COMMAND ----------

model_version_infos = client.search_model_versions(f"name = '{model_name}'")
new_model_version = max([model_version_info.version for model_version_info in model_version_infos])

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Add a description to this new version.

# COMMAND ----------

client.update_model_version(
    name=model_name,
    version=new_model_version,
    description=f"This model version is a ridge classification model with an alpha value of {alpha} that was trained in scikit-learn."
)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Since this model is now in staging, you can execute an automated CI/CD pipeline against it to test it before going into production.  Once that is completed, you can push that model into production.

# COMMAND ----------

client.transition_model_version_stage(
    name=model_name,
    version=new_model_version,
    stage="Production", 
    archive_existing_versions=True # Archive existing model in production 
)

# COMMAND ----------

# MAGIC %md
# MAGIC Exit notebook when running as a workflow task

# COMMAND ----------

dbutils.notebook.exit("End of notebook when running as a workflow task")

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ### Delete models
# MAGIC
# MAGIC Delete version 1.  
# MAGIC
# MAGIC NOTE!!! You cannot delete a model that is not first archived.

# COMMAND ----------

client.delete_model_version(
    name=model_name,
    version=1
)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Archive version 2 of the model too.

# COMMAND ----------

client.transition_model_version_stage(
    name=model_name,
    version=2,
    stage="Archived"
)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Now delete the entire registered model.

# COMMAND ----------

client.delete_registered_model(model_name)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ## Review
# MAGIC **Question:** How does MLflow tracking differ from the model registry?  
# MAGIC **Answer:** Tracking is meant for experimentation and development.  The model registry is designed to take a model from tracking and put it through staging and into production.  This is often the point that a data engineer or a machine learning engineer takes responsibility for the deployment process.
# MAGIC
# MAGIC **Question:** Why do I need a model registry?  
# MAGIC **Answer:** Just as MLflow tracking provides end-to-end reproducibility for the machine learning training process, a model registry provides reproducibility and governance for the deployment process.  Since production systems are mission critical, components can be isolated with ACL's so only specific individuals can alter production models.  Version control and CI/CD workflow integration is also a critical dimension of deploying models into production.
# MAGIC
# MAGIC **Question:** What can I do programmatically versus using the UI?  
# MAGIC **Answer:** Most operations can be done using the UI or in pure Python.  A model must be tracked using Python, but from that point on everything can be done either way.  For instance, a model logged using the MLflow tracking API can then be registered using the UI and can then be pushed into production.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ## Topics & Resources on the MLflow Model Registry
# MAGIC
# MAGIC Check out <a href="https://mlflow.org/docs/latest/registry.html" target="_blank">the MLflow documentation</a>
