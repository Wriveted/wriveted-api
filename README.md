
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

Set the environment variable `SQLALCHEMY_DATABASE_URI` with the path:

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
