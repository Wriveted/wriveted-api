#! /usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

python app/db/check_can_connect_to_db.py
alembic upgrade head
