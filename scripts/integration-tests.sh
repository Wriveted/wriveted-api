#!/usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

# Env vars to enable buildkit for docker-compose
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export DATABASE_POOL_SIZE=2
export DATABASE_MAX_OVERFLOW=0

# Conditional tag variable for image cache
if [[ -n "${PR_NUMBER}" ]]; then
  export TAG="PR-${PR_NUMBER}"
else
  export TAG="latest"
fi

# Remove possibly previous broken stacks left hanging after an error
docker compose -f docker-compose.yml down -v --remove-orphans
docker compose build --build-arg INSTALL_DEV=true --build-arg BUILDKIT_INLINE_CACHE=1
docker compose -f docker-compose.yml up -d db migration
docker compose logs migration
sleep 5

docker compose -f docker-compose.yml up -d api internal

# Now start the integration tests
docker compose exec -T api python app/db/check_can_connect_to_db.py
docker compose exec -T api bash /app/scripts/start-tests.sh "$@"
