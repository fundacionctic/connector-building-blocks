import json
import logging
import pprint
from typing import Union

import jwt
import uvicorn
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from typing_extensions import Annotated

from edcpy.config import AppConfig
from edcpy.messaging import (
    HTTP_PULL_QUEUE_ROUTING_KEY,
    HTTP_PUSH_QUEUE_ROUTING_KEY,
    HttpPullMessage,
    HttpPushMessage,
    MessagingApp,
    start_messaging_app,
)

_logger = logging.getLogger(__name__)

app = FastAPI()


class EndpointDataReference(BaseModel):
    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: dict


_state = {
    "messaging_app": None,
}


async def get_messaging_app() -> Union[MessagingApp, None]:
    if _state.get("messaging_app", None) is not None:
        return _state["messaging_app"]

    try:
        msg_app = await start_messaging_app()
        _state["messaging_app"] = msg_app
        return _state["messaging_app"]
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


@app.post("/pull")
async def http_pull_endpoint(
    item: EndpointDataReference, messaging_app: MessagingAppDep
):
    _logger.debug(
        "Received HTTP Pull request %s:\n%s",
        EndpointDataReference,
        pprint.pformat(item.dict()),
    )

    decoded_auth_code = _decode_auth_code(item)

    message = HttpPullMessage(
        auth_code_decoded=decoded_auth_code,
        auth_code=item.authCode,
        auth_key=item.authKey,
        endpoint=item.endpoint,
        id=item.id,
        properties=item.properties,
    )

    await messaging_app.broker.publish(
        message=message,
        routing_key=HTTP_PULL_QUEUE_ROUTING_KEY,
        exchange=messaging_app.exchange,
    )

    return {
        "broker": str(messaging_app.broker),
        "exchange": str(messaging_app.exchange),
    }


@app.post("/push")
async def http_push_endpoint(body: dict, messaging_app: MessagingAppDep):
    _logger.debug("Received HTTP Push request:\n%s", pprint.pformat(body))
    message = HttpPushMessage(body=body)

    await messaging_app.broker.publish(
        message=message,
        routing_key=HTTP_PUSH_QUEUE_ROUTING_KEY,
        exchange=messaging_app.exchange,
    )

    return {
        "broker": str(messaging_app.broker),
        "exchange": str(messaging_app.exchange),
    }


def run_server():
    """Run the HTTP server that exposes the HTTP API backend."""

    port = AppConfig.from_environ().http_api_port
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
