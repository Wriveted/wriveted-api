<div align="center">

# Wriveted API

![python](https://img.shields.io/badge/python-%233776AB.svg?style=flat-square&logo=python&logoColor=white)
![fastapi](https://img.shields.io/badge/fastapi-%23009688.svg?logo=fastapi&logoColor=white&style=flat-square)
![postgresql](https://img.shields.io/badge/postgresql-%234169E1.svg?style=flat-square&logo=postgresql&logoColor=white)
![sqlalchemy](https://img.shields.io/badge/sqlalchemy-%23D71F00.svg?style=flat-square&logo=sqlalchemy&logoColor=white)
![googlecloud](https://img.shields.io/badge/googlecloud-%234285F4.svg?style=flat-square&logo=googlecloud&logoColor=white)
![firebase](https://img.shields.io/badge/firebase-%23FFCA28.svg?style=flat-square&logo=firebase&logoColor=black)

</div>

## Overview

The core API for the [Huey Books](https://hueybooks.com) reading recommendation platform. A single Docker image contains two separate FastAPI applications:

- **Public API** (`app.main:app`) -- REST API for users, books, schools, collections, chatflows, and the CMS. Documented at [api.wriveted.com/v1/docs](https://api.wriveted.com/v1/docs).
- **Internal API** (`app.internal_api:internal_app`) -- background task processing, webhook handling, log ingestion.

Both are deployed as separate Cloud Run services backed by PostgreSQL (Cloud SQL), with Google Cloud Tasks providing queuing between them.

<p align="center">
  <img alt="Deployment Context" src="https://github.com/Wriveted/wriveted-api/blob/main/.github/context.png?raw=true" width="70%" />
</p>

### Key domain areas

| Domain | Description |
|--------|-------------|
| **Users** | Joined-table inheritance: Student, Educator, Parent, SchoolAdmin, etc. |
| **Books** | Work / Edition / CollectionItem hierarchy with AI-powered Labels |
| **Schools & Collections** | Library collections, class groups, activity tracking |
| **Chatflows** | Flow-based conversation engine powering Huey the Bookbot |
| **CMS** | Content management for chatflow questions, jokes, facts, messages |

## Quick start

```bash
# Build and start the stack (API + internal + PostgreSQL)
docker compose up -d --build

# Apply database migrations
docker compose run --rm migration

# Seed sample data (school, users, books, CMS content, flows)
docker compose run --rm --entrypoint python \
  -v "$PWD/scripts:/app/scripts" \
  api /app/scripts/seed_admin_ui_data.py --emit-tokens --tokens-format json
```

The public API is available at `http://localhost:8000`. The seed script prints JWTs for each user role so you can authenticate immediately.

> **Note:** The `api` service volume-mounts `./app` so code changes are live without rebuild. The `scripts/` directory is _not_ mounted by default -- the seed command above uses `-v` to mount it explicitly.

## Chatflow runtime

The chat runtime (`app/services/chat_runtime.py`) drives Huey's interactive reading-preference conversations. Flows are directed graphs of nodes (messages, questions, actions, conditions) defined in the admin UI and stored as JSON.

Key components:

- **NodeProcessors** -- `MessageNodeProcessor`, `QuestionNodeProcessor`, `ActionNodeProcessor`, `ConditionNodeProcessor` handle each node type.
- **Action processor** (`app/services/action_processor.py`) -- executes `set_variable`, `api_call`, and `aggregate` actions within flows.
- **CEL evaluator** (`app/services/cel_evaluator.py`) -- evaluates conditions and expressions using a custom CEL implementation with registered functions (`merge`, `top_keys`, etc.).
- **Variable resolver** (`app/services/variable_resolver.py`) -- `substitute_object` resolves `{{var}}` templates while preserving types; `substitute_variables` always returns strings.

### CMS

CMS content (questions, messages, jokes, facts) is managed via the API and surfaced in chatflows through content sources. The `CmsRepository` (`app/repositories/cms_repository.py`) supports random content selection, tag-based filtering, and age-appropriate content filtering.

### Flow fixtures

- **Seed fixture**: `scripts/fixtures/admin-ui-seed.json` -- declarative definition of schools, users, books, CMS content, and flow references.
- **Huey Bookbot flow**: `scripts/fixtures/huey-bookbot-flow.json` -- the production reading-preference flow.

## Testing

### Unit tests (no database required)

```bash
poetry run pytest app/tests/unit/ -v
```

### Integration tests (Docker)

The recommended way to run integration tests -- provides a proper environment with database migrations and all dependencies:

```bash
bash scripts/integration-tests.sh
```

Ensure no conflicting PostgreSQL containers are running on port 5432.

### Single test

```bash
poetry run pytest -v app/tests/integration/test_specific.py::test_function
```

### E2E flow test

Requires a running Docker stack with seeded data:

```bash
python scripts/test_huey_flow_e2e.py
```

## Database migrations

Uses [Alembic](https://alembic.sqlalchemy.org/) with SQLAlchemy 2.0 models. PostgreSQL functions and triggers are defined declaratively in Python using `alembic_utils` (`app/db/functions.py`, `app/db/triggers.py`).

```bash
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/postgres

# Apply all migrations
poetry run alembic upgrade head

# Create a new migration after modifying models
poetry run alembic revision --autogenerate -m "Description"
```

Workflow: modify models in `app/models/` -> add imports to `app/models/__init__.py` -> generate migration -> review the generated file -> apply.

## Code quality

```bash
# Lint
poetry run ruff check

# Auto-fix
poetry run ruff check --fix

# Pre-commit hooks (install once, then runs on every commit)
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Authentication & authorization

- **Firebase Authentication** -- users authenticate via Firebase, then exchange the token for a Wriveted JWT at `/v1/auth/firebase`.
- **RBAC** -- role-based access control with principals (`user-xyz`, `school-1`). Endpoints define ACLs specifying required permissions per role.
- **Service Accounts** -- long-lived tokens for LMS integrations.

## Deployment

Deployed to GCP Cloud Run (public + internal services) backed by Cloud SQL. See the [GCP deployment section](#google-cloud-platform) below for details.

### Google Cloud Platform

Build and deploy:

```bash
gcloud builds submit --tag gcr.io/wriveted-api/wriveted-api

gcloud run deploy wriveted-api \
  --image gcr.io/wriveted-api/wriveted-api \
  --add-cloudsql-instances=wriveted \
  --platform managed \
  --set-env-vars="POSTGRESQL_DATABASE_SOCKET_PATH=/cloudsql" \
  --set-secrets=POSTGRESQL_PASSWORD=wriveted-api-cloud-sql-password:latest,SECRET_KEY=wriveted-api-secret-key:latest
```

### Production database migrations

```bash
# Start Cloud SQL proxy
cloud_sql_proxy -instances=wriveted-api:australia-southeast1:wriveted=tcp:5432

# Apply migrations through the proxy
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/postgres
poetry run alembic upgrade head
```

Production logs: [Cloud Run console](https://console.cloud.google.com/run/detail/australia-southeast1/wriveted-api/logs?project=wriveted-api)
