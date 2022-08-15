#!/usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

# set env variables
export SENDGRID_API_KEY=unused-key-set-for-testing
export SHOPIFY_HMAC_SECRET=unused-key-set-for-testing

# Remove possibly previous broken stacks left hanging after an error
docker-compose -f docker-compose.yml down -v --remove-orphans
docker-compose build --build-arg INSTALL_DEV=true
docker-compose -f docker-compose.yml up -d
docker-compose logs
sleep 5

# Now start the integration tests
docker-compose exec -T api python app/db/check_can_connect_to_db.py
docker-compose exec -T api bash /app/scripts/start-tests.sh "$@"
