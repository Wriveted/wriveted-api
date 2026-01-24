#!/usr/bin/env bash

set -eo pipefail

if [[ -z "${PR_NUMBER}" ]]; then
  echo "PR_NUMBER is required" >&2
  exit 1
fi

if [[ -z "${POSTGRESQL_PASSWORD}" ]]; then
  echo "POSTGRESQL_PASSWORD is required" >&2
  exit 1
fi

POSTGRESQL_USER="${POSTGRESQL_USER:-postgres}"
PR_DATABASE="wriveted_pr_${PR_NUMBER}"

socket_path="${POSTGRESQL_DATABASE_SOCKET_PATH:-}"
project_id="${GCP_PROJECT_ID:-}"
location="${GCP_LOCATION:-}"
instance_id="${GCP_CLOUD_SQL_INSTANCE_ID:-}"

if [[ -z "${socket_path}" || -z "${project_id}" || -z "${location}" || -z "${instance_id}" ]]; then
  echo "Cloud SQL socket configuration is required (POSTGRESQL_DATABASE_SOCKET_PATH, GCP_PROJECT_ID, GCP_LOCATION, GCP_CLOUD_SQL_INSTANCE_ID)." >&2
  exit 1
fi

export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://${POSTGRESQL_USER}:${POSTGRESQL_PASSWORD}@/postgres?host=${socket_path}/${project_id}:${location}:${instance_id}"
export PR_DATABASE

python - <<'PY'
import os
import re
from sqlalchemy import create_engine, text

db_name = os.environ["PR_DATABASE"]
if not re.fullmatch(r"[a-z0-9_]+", db_name):
    raise SystemExit(f"Invalid PR database name: {db_name}")

engine = create_engine(os.environ["SQLALCHEMY_DATABASE_URI"], isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname=:name"),
        {"name": db_name},
    ).scalar()
    if not exists:
        print(f"Database {db_name} does not exist, skipping")
        raise SystemExit(0)

    conn.execute(
        text(
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname=:name AND pid <> pg_backend_pid()"
        ),
        {"name": db_name},
    )
    conn.execute(text(f'DROP DATABASE "{db_name}"'))
    print(f"Dropped database {db_name}")
PY
