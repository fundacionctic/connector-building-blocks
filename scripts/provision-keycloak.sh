#!/usr/bin/env bash

set -e
set -x

BASE_DIR=/vagrant

cd ${BASE_DIR}
docker compose -f ./docker-compose-keycloak.yml up -d --build --wait
task create-keycloak-client-example-provider
task create-keycloak-client-example-consumer
