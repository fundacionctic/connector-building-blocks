#!/usr/bin/env bash

set -e

: "${KEYSTORE_PATH:?}"
: "${KEYSTORE_PASSWORD:?}"
: "${PATH_APP:?}"

echo "Dumping certificate from keystore '${KEYSTORE_PATH}' to Vault properties file..."

openssl pkcs12 -in ${KEYSTORE_PATH} -nodes -nokeys -passin pass:${KEYSTORE_PASSWORD} |
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >/tmp/cert.pem

echo "publickey=$(cat /tmp/cert.pem)" >/tmp/vault.properties.temp
sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\r\\n/g' /tmp/vault.properties.temp >${PATH_APP}/vault.properties
