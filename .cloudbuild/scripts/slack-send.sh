#!/bin/bash

pr_number="$1"
url_suffix="wriveted-api-development-lg5ntws4da-ts.a.run.app"
deployment_url="https://${pr_number}---${url_suffix}"
slack_message=":rocket: $(wriveted-api) [PR ${pr_number}]: <${deployment_url}|${deployment_url}> "

curl -X POST \
  -H 'Content-type: application/json; charset=utf-8' \
  --data "{ \"text\": \"${slack_message}\" }" \
  "${SLACK_WEBHOOK}"
