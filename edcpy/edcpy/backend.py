import json
import logging
import os
import pprint
from typing import Union

import coloredlogs
import jwt
import requests
import uvicorn
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from typing_extensions import Annotated

from edcpy.config import AppConfig
from edcpy.messaging import MessagingApp, start_messaging_app

_logger = logging.getLogger(__name__)

app = FastAPI()


class EndpointDataReference(BaseModel):
    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: dict


async def get_messaging_app() -> Union[MessagingApp, None]:
    try:
        return await start_messaging_app()
    except:
        _logger.warning("Could not start messaging app", exc_info=True)
        return None


MessagingAppDep = Annotated[Union[MessagingApp, None], Depends(get_messaging_app)]


def _read_public_key() -> str:
    """Read the public key from the certificate file specified by the
    EDC_CERT_PATH environment variable."""

    cert_path = AppConfig.from_environ().cert_path
    assert cert_path, "EDC_CERT_PATH environment variable not set"

    with open(cert_path, "rb") as fh:
        cert_str = fh.read()
        cert_obj = load_pem_x509_certificate(cert_str, default_backend())

        public_key = cert_obj.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        _logger.debug(
            "Public key read from certificate '%s':\n%s", cert_path, public_key.decode()
        )

        return public_key


def _decode_auth_code(item: EndpointDataReference) -> dict:
    """Decode the EndpointDataReference element received from the data space."""

    decode_kwargs = {
        "key": _read_public_key(),
        "algorithms": ["RS256"],
        "options": {"verify_signature": True},
    }

    _logger.debug("JWT decode kwargs:\n%s", pprint.pformat(decode_kwargs))

    ret = jwt.decode(jwt=item.authCode, **decode_kwargs)

    ret["dad"] = json.loads(ret["dad"])

    ret["dad"]["properties"]["authCode"] = jwt.decode(
        ret["dad"]["properties"]["authCode"], options={"verify_signature": False}
    )

    return ret


def _get_method(decoded_auth_code: dict) -> Union[str, None]:
    source_json_dad = (
        decoded_auth_code.get("dad", {})
        .get("properties", {})
        .get("authCode", {})
        .get("dad")
    )

    if not source_json_dad:
        return None

    try:
        props = json.loads(source_json_dad)["properties"]
    except:
        _logger.warning("Could not parse HttpData properties from decoded auth code")
        return None

    return next((val for key, val in props.items() if key.endswith("method")), None)


@app.post("/pull")
async def http_pull_endpoint(
    item: EndpointDataReference, messaging_app: MessagingAppDep
):
    _logger.debug(
        "Received %s:\n%s",
        EndpointDataReference,
        pprint.pformat(item.dict()),
    )

    decoded_auth_code = _decode_auth_code(item)
    method = _get_method(decoded_auth_code)
    method = method if method is not None else "GET"

    _logger.debug(
        "Decoded authCode %s:\n%s",
        EndpointDataReference,
        pprint.pformat(decoded_auth_code),
    )

    _logger.info("Sending %s request to: %s", method, item.endpoint)

    res = requests.request(
        method=method, url=item.endpoint, headers={item.authKey: item.authCode}
    )

    _logger.info(
        "Response from %s:\n%s",
        item.endpoint,
        pprint.pformat(res.text),
    )

    return item


@app.post("/push")
async def http_push_endpoint(body: dict, messaging_app: MessagingAppDep):
    _logger.info("Received request with body:\n%s", pprint.pformat(body))
    return {"ok": True}


def run_server():
    """Run the server."""

    port = AppConfig.from_environ().http_api_port
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
