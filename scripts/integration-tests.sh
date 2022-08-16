#!/usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

# Remove possibly previous broken stacks left hanging after an error
echo "docker-compose -f docker-compose.yml down -v --remove-orphans"
docker-compose -f docker-compose.yml down -v --remove-orphans
echo "docker-compose build --build-arg INSTALL_DEV=true"
docker-compose build --build-arg INSTALL_DEV=true

docker-compose -f docker-compose.yml up -d
echo "docker-compose -f docker-compose.yml up -d"
docker-compose logs
echo "docker-compose logs"
sleep 5
echo "sleep 5"

# Now start the integration tests
echo "docker-compose exec -T api python app/db/check_can_connect_to_db.py"
docker-compose exec -T api python app/db/check_can_connect_to_db.py
echo 'docker-compose exec -T api bash /app/scripts/start-tests.sh' $*
docker-compose exec -T api bash /app/scripts/start-tests.sh "$@"
