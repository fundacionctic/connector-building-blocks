#!/usr/bin/env bash

set -e
set -x

conn_str="DefaultEndpointsProtocol=http;AccountName=company1assets;AccountKey=key1;BlobEndpoint=http://127.0.0.1:10000/company1assets;"

az storage container create --name src-container --connection-string $conn_str

az storage blob upload \
    -f /mvd/deployment/azure/terraform/modules/participant/sample-data/text-document.txt \
    --overwrite \
    --container-name src-container \
    --name text-document.txt \
    --connection-string $conn_str
