# Databricks notebook source
# MAGIC  %md-sandbox
# MAGIC
# MAGIC <div style="text-align: left; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://s3.eu-central-1.amazonaws.com/co.lever.eu.client-logos/c2f22a4d-adbd-49a9-a9ca-c24c0bd5dc1a-1607101144408.png" alt="D ONE" style="width: 300px">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 400px">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Registry in Unity catalog
# MAGIC
# MAGIC Model Registry in Unity catalog builds on top of MLflow Model Registry is a collaborative hub where teams can share ML models, work together from experimentation to online testing and production, integrate with approval and governance workflows, and monitor ML deployments and their performance.  This notebook explores how to manage models using the MLflow model registry.
# MAGIC
# MAGIC
# MAGIC In this notebook we will:
# MAGIC  - Register a model using MLflow
# MAGIC  - Manage the model lifecycle
# MAGIC  - Alias and delete models
# MAGIC
# MAGIC Registering models in Unity Catalog allows:<br><br>
# MAGIC
# MAGIC * Namespacing and governance for models.
# MAGIC * Sharing of models across:
# MAGIC   * workspaces in the same metastore (UC)
# MAGIC   * workspaces in other metastores (Delta Sharing)
# MAGIC * Centralized access control, auditing, lineage, and model discovery across workspaces.
# MAGIC * Model deployment via aliases.
# MAGIC
# MAGIC See <a href="https://docs.databricks.com/en/machine-learning/manage-model-lifecycle/index.html#manage-model-lifecycle-in-unity-catalog" target="_blank">the Databricks docs</a> for more details on the  registering models in Unity Catalog.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC
# MAGIC ### Registering a Model
# MAGIC
# MAGIC The following workflow will work with either the UI or in pure Python.  This notebook will use pure Python.
# MAGIC
# MAGIC Explore the UI throughout this NOTEBOOK by clicking the "Catalog" tab on the left-hand side of the screen and navigating to the catalog and schema you will be using throughout this exercise.

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

# grant create model access to tour schema
spark.sql(f"GRANT CREATE_MODEL ON SCHEMA {catalog_name}.{schema_name} TO `{user_email}`")

# COMMAND ----------

# set registry to your UC
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------

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

model_name = f"{catalog_name}.{schema_name}.lr_model"
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
# MAGIC  **Open the *Catalog* tab on the left of the screen, navifate to your user catalog and silver schema and explore the registered model.**  Note the following:<br><br>
# MAGIC
# MAGIC * It logged who trained the model and what code was used
# MAGIC * It logged a history of actions taken on this model
# MAGIC * It logged this model as a first version

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
# MAGIC ### Managing a Model
# MAGIC
# MAGIC Model aliases and tags help you organize and manage models in Unity Catalog.
# MAGIC
# MAGIC Model aliases allow you to assign a mutable, named reference to a particular version of a registered model. You can use aliases to indicate the deployment status of a model version. For example, you could allocate a “Champion” alias to the model version currently in production and target this alias in workloads that use the production model. You can then update the production model by reassigning the “Champion” alias to a different model version.
# MAGIC
# MAGIC Tags are key-value pairs that you associate with registered models and model versions, allowing you to label and categorize them by function or status.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC
# MAGIC Now that you've learned about aliases and tags, set the model alias to **`Champion`**.

# COMMAND ----------

import time

time.sleep(5) # In case the registration is still pending

# COMMAND ----------

alias = "Champion"

client.set_registered_model_alias(
    name=model_details.name, 
    alias=alias,
    version=model_details.version
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
print(f"The current model alias is: '{model_version_details.aliases[0]}'")

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
# MAGIC ### Registering a New Model Version
# MAGIC
# MAGIC The MLflow Model Registry enables you to create multiple model versions corresponding to a single registered model. By performing stage transitions, you can seamlessly integrate new model versions into your staging or production environments.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Create a new model version and register that model when it's logged.

# COMMAND ----------

from sklearn.linear_model import RidgeClassifier

# signature required for UC registry
from mlflow.models import infer_signature
signatures = X_train.sample(2)

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
        input_example=signatures
    )

    mlflow.log_params(ridge_classifier.get_params())
    mlflow.log_metric("f1_score_ridge", f1_score(y_test, ridge_classifier.predict(X_test)))

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Alias the new model as 'Candidate'.

# COMMAND ----------

alias = "Candidate"

client.set_registered_model_alias(
    name=model_details.name, 
    alias=alias,
    version=2
)

# COMMAND ----------

# MAGIC %md-sandbox <i18n value="fe857eeb-6119-4927-ad79-77eaa7bffe3a"/>
# MAGIC
# MAGIC
# MAGIC
# MAGIC Check the UI to see the new model version.
# MAGIC

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
# MAGIC Since this model is now a candidate for production, you would execute an automated CI/CD pipeline against it to test it before going into production.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Go to the UI. You will see that your alias for Version 2 of your model has been set to 'candidate', and Version 1 is still aliased as 'champion'.
# MAGIC
# MAGIC After you have done your tests, you would promote your 'Candidate' model to 'Champion'. You can load your model just by using its alias, and then set the new alias as before.

# COMMAND ----------

alias = "candidate"

# get the model aliased as 'candidate'
latest_model = client.get_model_version_by_alias(
    name=model_details.name, 
    alias=alias,
)

# and set that version as champion
new_alias = "champion"

client.set_registered_model_alias(
    name=latest_model.name, 
    alias=new_alias,
    version=latest_model.version
)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC Go to the UI. You will see that your alias for Version 2 of your model has been updated to 'champion, but it is still also aliased as 'candidate' too. This is because while a model version can have multiple aliases, there can be no same alias for between versions of the same model. That is why Version 1 automatically lost the alias 'champion'.

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

# COMMAND ----------

client.delete_model_version(
    name=model_name,
    version=1
)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Delete version 2 of the model too.

# COMMAND ----------

client.delete_model_version(
    name=model_name,
    version=2
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
# MAGIC **Answer:** Tracking is meant for experimentation and development.  The model registry is designed to take a model from tracking and put it into model lifecycle management.  This is often the point that a data engineer or a machine learning engineer takes responsibility for the deployment process.
# MAGIC
# MAGIC **Question:** Why do I need a model registry?  
# MAGIC **Answer:** Just as MLflow tracking provides end-to-end reproducibility for the machine learning training process, a model registry provides reproducibility and governance for the deployment process.  Since production systems are mission critical, components can be isolated with ACL's so only specific individuals can alter production models.  Version control and CI/CD workflow integration is also a critical dimension of deploying models into production.
# MAGIC
# MAGIC **Question:** What can I do programmatically versus using the UI?  
# MAGIC **Answer:** Most operations can be done using the UI or in pure Python.  A model must be tracked using Python, but from that point on everything can be done either way.  For instance, a model logged using the MLflow tracking API can then be registered using the UI and can then be aliased or tagged.

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ## Topics & Resources on the Model Registry with UC
# MAGIC
# MAGIC Check out <a href="https://docs.databricks.com/en/machine-learning/manage-model-lifecycle/index.html#manage-model-lifecycle-in-unity-catalog" target="_blank">the Databricks documentation</a>
