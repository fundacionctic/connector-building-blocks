import json
import logging
import os
import pprint

import coloredlogs
import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from fastapi import FastAPI
from pydantic import BaseModel

_CERT_PATH = os.getenv(
    "CERT_PATH",
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "../datacellar-certs/cert.pem"
    ),
)

coloredlogs.install(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = FastAPI()


class EndpointDataReference(BaseModel):
    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: dict


def _decode_endpoint_data_ref(item: EndpointDataReference) -> dict:
    with open(_CERT_PATH, "rb") as fh:
        cert_str = fh.read()
        cert_obj = load_pem_x509_certificate(cert_str, default_backend())
        public_key = cert_obj.public_key()

    decode_kwargs = {"key": public_key, "algorithms": ["RS256"]}

    ret = jwt.decode(item.authCode, **decode_kwargs)

    ret["dad"] = json.loads(ret["dad"])

    ret["dad"]["properties"]["authCode"] = jwt.decode(
        ret["dad"]["properties"]["authCode"], **decode_kwargs
    )

    return ret


@app.post("/")
async def root(item: EndpointDataReference):
    _logger.debug(
        "Received %s:\n%s",
        EndpointDataReference,
        pprint.pformat(item.dict()),
    )

    decoded = _decode_endpoint_data_ref(item)

    _logger.debug(
        "Decoded %s:\n%s",
        EndpointDataReference,
        pprint.pformat(decoded),
    )

    _logger.info("Sending request to: %s", item.endpoint)

    res = requests.get(item.endpoint, headers={item.authKey: item.authCode})

    _logger.info(
        "Response from %s:\n%s",
        item.endpoint,
        pprint.pformat(res.text),
    )

    return item
