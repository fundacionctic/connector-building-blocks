#!/usr/bin/env bash

: "${PATH_CONNECTOR:?}"
: "${PROPERTIES_FILE_PATH:?}"
: "${KEYSTORE_PATH:?}"
: "${KEYSTORE_PASSWORD:?}"

set -eo pipefail

API_AUTH_KEY_ALIAS=$(grep "^edc.api.auth.key.alias=" "${PROPERTIES_FILE_PATH}" | cut -d'=' -f2)

if [ -n "${API_AUTH_KEY_ALIAS}" ]; then
    echo "Read API auth key alias from properties file: ${API_AUTH_KEY_ALIAS}"
fi

echo "Generating Vault properties file..."

OUT_DIR=${PATH_CONNECTOR} \
    API_AUTH_KEY=${API_AUTH_KEY} \
    API_AUTH_KEY_ALIAS=${API_AUTH_KEY_ALIAS} \
    ${PATH_CONNECTOR}/generate-vault.sh

echo "Starting connector runtime..."

exec java \
    -Dedc.fs.config=${PROPERTIES_FILE_PATH} \
    -Dedc.vault=${PATH_CONNECTOR}/vault.properties \
    -Dedc.keystore=${KEYSTORE_PATH} \
    -Dedc.keystore.password=${KEYSTORE_PASSWORD} \
    -jar ${PATH_CONNECTOR}/openapi-connector/build/libs/openapi-connector.jar
