#!/bin/bash

set -eo pipefail

CLOUD_SQL_INSTANCE="wriveted-api:australia-southeast1:wriveted-development"
POSTGRES_PORT="5432"

if [[ -z "${PR_NUMBER}" ]]; then
  echo "PR_NUMBER is required" >&2
  exit 1
fi

if [[ -z "${POSTGRESQL_ROOT_PASSWORD}" ]]; then
  echo "POSTGRESQL_ROOT_PASSWORD is required" >&2
  exit 1
fi

PR_DATABASE="wriveted_pr_${PR_NUMBER}"
POSTGRESQL_APP_USER="${POSTGRESQL_APP_USER:-cloudrun}"

proxy_connection_cleanup() {
  echo "cleaning up cloud_sql_proxy connection"
  kill "$(jobs -p)"
}
trap proxy_connection_cleanup EXIT SIGTERM SIGINT SIGQUIT

echo "Downloading cloud_sql_proxy"
curl -s "https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64" -o "${HOME}/cloud_sql_proxy"
chmod +x "${HOME}/cloud_sql_proxy"
"${HOME}/cloud_sql_proxy" -instances="${CLOUD_SQL_INSTANCE}=tcp:localhost:${POSTGRES_PORT}" &

export SQLALCHEMY_DATABASE_URI="postgresql://postgres:${POSTGRESQL_ROOT_PASSWORD}@localhost/postgres"
export PR_DATABASE
export POSTGRESQL_APP_USER

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
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        print(f"Created database {db_name}")
    else:
        print(f"Database {db_name} already exists")
    app_user = os.environ.get("POSTGRESQL_APP_USER", "cloudrun")
    conn.execute(text(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{app_user}"'))
PY

export SQLALCHEMY_DATABASE_URI="postgresql://postgres:${POSTGRESQL_ROOT_PASSWORD}@localhost/${PR_DATABASE}"
scripts/run-migrations.sh
