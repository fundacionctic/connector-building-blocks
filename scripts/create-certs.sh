#!/usr/bin/env bash

set -e
set -x

: "${OUT_DIR:?}"
: "${KEY_ALIAS:?}"
: "${KEY_PASSW:?}"

apt-get update -y && apt-get install -y openssh-client openssl

openssl req -x509 \
    -nodes \
    -newkey rsa:4096 \
    -keyout ${OUT_DIR}/key.pem \
    -out ${OUT_DIR}/cert.pem \
    -days 365 \
    -subj "/C=ES/ST=Asturias/L=Gijon/O=CTIC/OU=CTIC/CN=www.datacellar.eu"

openssl pkcs12 -export \
    -in ${OUT_DIR}/cert.pem \
    -inkey ${OUT_DIR}/key.pem \
    -out ${OUT_DIR}/cert.pfx \
    -name ${KEY_ALIAS} \
    -passout pass:${KEY_PASSW}

echo "publickey=$(cat ${OUT_DIR}/cert.pem)" > \
    ${OUT_DIR}/vault.properties.temp

sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\r\\n/g' ${OUT_DIR}/vault.properties.temp > \
    ${OUT_DIR}/vault.properties

rm ${OUT_DIR}/vault.properties.temp
