#! /usr/bin/env bash

# Set bash to exit immediately on any command failure
set -e

poetry run pytest -v app/tests
