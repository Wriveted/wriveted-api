#!/bin/bash

set -eo pipefail

CLOUD_SQL_INSTANCE="wriveted-api:australia-southeast1:wriveted"
POSTGRES_PORT="5432"

# trap signals to kill the background connection process
proxy_connection_cleanup() {
  echo "cleaning up cloud_sql_proxy connection"
  kill "$(jobs -p)"
}
trap proxy_connection_cleanup EXIT SIGTERM SIGINT SIGQUIT

echo "Downloading cloud_sql_proxy"
curl -s "https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64" -o cloud_sql_proxy
chmod +x cloud_sql_proxy
./cloud_sql_proxy -instances="${CLOUD_SQL_INSTANCE}=tcp:localhost:${POSTGRES_PORT}" &

echo "Running migration"
export SQLALCHEMY_DATABASE_URI="postgresql://postgres:${POSTGRESQL_PASSWORD}@localhost/postgres"
scripts/run-migrations.sh
