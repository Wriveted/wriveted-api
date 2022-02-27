#! /usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e
SCRIPT_DIR=$(dirname "$0")


# Remove possibly previous broken stacks left hanging after an error
docker-compose -f docker-compose.yml down -v --remove-orphans
docker-compose build --build-arg INSTALL_DEV=true

docker-compose -f docker-compose.yml up -d

docker-compose logs
sleep 5

# Now exec into the application to run migrations
docker-compose exec -e SQLALCHEMY_DATABASE_URI=postgresql://postgres:xvc8kcn@db/postgres -T api bash /app/scripts/run-migrations.sh

# Now start the integration tests
docker-compose exec -T api bash /app/scripts/start-tests.sh "$@"
