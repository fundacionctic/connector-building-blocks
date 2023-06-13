#!/usr/bin/env bash

set -e
set -x

cd /vagrant/example
docker compose -f ./docker-compose-consumer.yml up -d --build --wait
