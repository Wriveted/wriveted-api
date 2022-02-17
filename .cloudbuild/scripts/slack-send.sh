#!/bin/bash

curl -X POST \
  -H 'Content-type: application/json; charset=utf-8' \
  --data "{ \"text\": \"pr-${_PR_NUMBER}---wriveted-api-development-lg5ntws4da-ts.a.run.app\" }" \
  "${SLACK_WEBHOOK}"
