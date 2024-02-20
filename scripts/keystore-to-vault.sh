#!/usr/bin/env bash

set -e

: "${KEYSTORE_PATH:?}"
: "${KEYSTORE_PASSWORD:?}"
: "${PATH_CONNECTOR:?}"

if [ -f ${PATH_CONNECTOR}/vault.properties ]; then
    echo "File '${PATH_CONNECTOR}/vault.properties' already exists. Exiting..."
    exit 0
fi

echo "Dumping certificate from keystore '${KEYSTORE_PATH}' to Vault properties file..."

TEMP_DIR=$(python3 -c "import tempfile; print(tempfile.gettempdir());")/coreconn

rm -fr ${TEMP_DIR} && mkdir -p ${TEMP_DIR}

# Extract the public key from the keystore
# Sed extracts the lines between -BEGIN CERTIFICATE- and -END CERTIFICATE-
openssl pkcs12 -in ${KEYSTORE_PATH} -nodes -nokeys -passin pass:${KEYSTORE_PASSWORD} |
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >${TEMP_DIR}/cert.pem

echo "publickey=$(cat ${TEMP_DIR}/cert.pem)" >${TEMP_DIR}/vault.properties.temp

# Replace all newline characters in the temporary Vault properties file with \r\n
sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\r\\n/g' ${TEMP_DIR}/vault.properties.temp >${PATH_CONNECTOR}/vault.properties
