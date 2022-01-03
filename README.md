
This repository implements a REST API to add, edit, and remove information about 
Users, Books, Schools and Library Collections for Wriveted.

The API is designed for use by multiple users:
* Library Management Systems. In particular see the section on updating and setting Schools collections.
* Wriveted Staff either directly via scripts or via an admin UI.
* End users via Huey chatbot or other Wriveted applications.


## Poetry

Install poetry, then install dependencies with:

```shell
poetry install
```

Add a new dependency e.g. `pydantic` with:

```shell
poetry add pydantic
```


## Database Migrations

Login to GCP:

```shell
gcloud auth application-default login
```

Start the [Cloud SQL proxy](https://cloud.google.com/sql/docs/postgres/quickstart-proxy-test?authuser=1).

```shell
cloud_sql_proxy -instances=hardbyte-wriveted-development:australia-southeast1:wriveted=tcp:5432
```

Set the environment variable `SQLALCHEMY_DATABASE_URI` with the proxied database path (otherwise it will create a local sqlite database):

```
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:gJduFxMylJN1v44B@localhost/postgres
```

Then create a new migration:

```shell
poetry run alembic revision --autogenerate -m "Create first tables"
```

Apply all migrations:

```shell
poetry run alembic upgrade head
```


# Deployment

## Google Cloud Platform

Cloud Build + Cloud SQL + Cloud Run

Build the Docker image using Cloud Build:

`gcloud builds submit --tag gcr.io/hardbyte-wriveted-development/wriveted-api`

Then deploy it (or use the Google Console):

```shell
gcloud run deploy wriveted-api \
  --image gcr.io/hardbyte-wriveted-development/wriveted-api \
  --add-cloudsql-instances=wriveted \
  --platform managed \
  --set-env-vars="POSTGRESQL_DATABASE_SOCKET_PATH=/cloudsql" \
  --set-secrets=POSTGRESQL_PASSWORD=wriveted-api-cloud-sql-password:latest,SECRET_KEY=wriveted-api-secret-key:latest
  
```

This will probably fail the first few times for a new GCP project - you'll have
to follow the clues to add appropriate permissions.
At a minimum you'll have to add the secrets to Secret Manager, then attach
the `roles/secretmanager.secretAccessor` role to the service account used by 
Cloud Run for those secrets.

You will be prompted to allow unauthenticated invocations: respond `y`. We 
implement our own authentication in the FastAPI app.

Note you will have to configure the Cloud SQL database manually 
(orchestrating with Terraform is left as an exercise for the reader 👋).

Use a public IP address for the Cloud SQL instance (don't worry about the
private VPC method it is way more expensive).
Smallest instance with shared CPU is fine 



## 🚨 Authorization

The API implements RBAC + row level access control on resources. Each user or service account
is linked to roles (e.g. `"admin"`, `"lms"`, or `"student"`) and principals (e.g. `user-xyz`,
`school-1`). Endpoints have access control lists that specify what permissions are required for
different principals to access the resource at that endpoint. For example to access a school
the access control list could look like this:

```python
access_control_list = [
    (Allow, "role:admin", "create"),
    (Allow, "role:admin", "read"),
    (Allow, "role:admin", "update"),
    (Allow, "role:admin", "delete"),
    (Allow, "role:admin", "batch"),

    (Allow, "role:lms", "batch"),
    (Allow, "role:lms", "update"),

    (Deny, "role:student", "update"),
    (Deny, "role:student", "delete"),

    (Allow, f"school:{self.id}", "read"),
    (Allow, f"school:{self.id}", "update"),
]
```
