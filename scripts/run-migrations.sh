#!/usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

python app/db/check_can_connect_to_db.py
pip show alembic
echo "Checking database and migration state"
alembic current
alembic heads
alembic upgrade head