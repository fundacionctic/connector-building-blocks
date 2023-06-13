#!/usr/bin/env bash

set -e
set -x

cd /vagrant/
task prepare-example
cd /vagrant/example
docker compose -f ./docker-compose-provider.yml up -d --build --wait