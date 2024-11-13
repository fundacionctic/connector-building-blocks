#!/usr/bin/env bash

set -e

: "${KEYSTORE_PATH:?}"
: "${KEYSTORE_PASSWORD:?}"
: "${OUT_DIR:?}"

if [ -f ${OUT_DIR}/vault.properties ]; then
    echo "File '${OUT_DIR}/vault.properties' already exists. Exiting..."
    exit 0
fi

echo "Dumping certificate from keystore '${KEYSTORE_PATH}' to Vault properties file '${OUT_DIR}/vault.properties'..."

TEMP_DIR=$(mktemp -d)/connector
mkdir -p ${TEMP_DIR}

# Extract the public key from the keystore
# Sed extracts the lines between -BEGIN CERTIFICATE- and -END CERTIFICATE-
openssl pkcs12 -in ${KEYSTORE_PATH} -nodes -nokeys -passin pass:${KEYSTORE_PASSWORD} |
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >${TEMP_DIR}/cert.pem

echo "publickey=$(cat ${TEMP_DIR}/cert.pem)" >${TEMP_DIR}/vault.properties.temp

# Replace all newline characters in the temporary Vault properties file with \r\n
sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\r\\n/g' ${TEMP_DIR}/vault.properties.temp >${OUT_DIR}/vault.properties

# Add the API key to the Vault properties file if it is set
if [ -n "${API_AUTH_KEY}" ] && [ -n "${API_AUTH_KEY_ALIAS}" ]; then
    echo "Adding API auth key with alias '${API_AUTH_KEY_ALIAS}' to Vault properties file '${OUT_DIR}/vault.properties'..."
    echo "${API_AUTH_KEY_ALIAS}=${API_AUTH_KEY}" >>${OUT_DIR}/vault.properties
else
    echo "API auth key value or alias not set. Skipping..."
fi
