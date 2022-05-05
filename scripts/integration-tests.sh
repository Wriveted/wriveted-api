#!/usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

# Remove possibly previous broken stacks left hanging after an error
docker-compose -f docker-compose.yml down -v --remove-orphans
docker-compose build --build-arg INSTALL_DEV=true
docker-compose -f docker-compose.yml up -d
docker-compose logs
sleep 5

# Now start the integration tests
docker-compose exec -T api bash /app/scripts/start-tests.sh "$@"
