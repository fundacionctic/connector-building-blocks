#!/usr/bin/env bash

set -e
set -x

BASE_DIR=/vagrant
POST_UP_SLEEP=15

cd ${BASE_DIR}
docker compose -f ./docker-compose-keycloak.yml up -d --build --wait
sleep ${POST_UP_SLEEP}
task create-keycloak-client-example-provider
task create-keycloak-client-example-consumer
