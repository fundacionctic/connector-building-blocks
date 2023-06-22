#!/usr/bin/env bash

set -e
set -x

BASE_DIR=/vagrant

cd ${BASE_DIR}
task create-example-certs-consumer

cd ${BASE_DIR}
docker compose -f ./docker-compose-consumer.yml up -d --build --wait
