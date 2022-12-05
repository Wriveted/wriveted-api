#!/bin/bash

set -eo pipefail

CLOUD_SQL_INSTANCE="wriveted-api:australia-southeast1:wriveted-development"
POSTGRES_PORT="5432"

# trap signals to kill the background connection process
proxy_connection_cleanup() {
  echo "cleaning up"
  kill "$(jobs -p)"
}
trap proxy_connection_cleanup EXIT SIGTERM SIGINT SIGQUIT

echo "Downloading cloud_sql_proxy"
wget -q "https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64" -O cloud_sql_proxy
chmod +x cloud_sql_proxy
./cloud_sql_proxy -instances="${CLOUD_SQL_INSTANCE}=tcp:127.0.0.1:${POSTGRES_PORT}" &

# We consider "curl: (52) Empty reply from server" as an established connection
echo "Waiting for proxy connection to establish..."
until grep -q "(52)" <(curl -L localhost:5432/ 2>&1); do
  echo "waiting..."
  sleep 2
done
echo "connection established"

echo "Running migration"
poetry run alembic upgrade head
