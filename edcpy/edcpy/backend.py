import json
import logging
import os
import pprint
from typing import AsyncGenerator

import coloredlogs
import jwt
import uvicorn
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, FastAPI
from pydantic import BaseModel  # pylint: disable=no-name-in-module
from slugify import slugify
from typing_extensions import Annotated

from edcpy.config import AppConfig, get_config
from edcpy.messaging import (
    BASE_HTTP_PULL_QUEUE_ROUTING_KEY,
    BASE_HTTP_PUSH_QUEUE_ROUTING_KEY,
    HttpPullMessage,
    HttpPushMessage,
    MessagingApp,
    with_messaging_app,
)

_logger = logging.getLogger(__name__)

app = FastAPI()


class EndpointDataReference(BaseModel):
    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: dict
    contractId: str


async def get_messaging_app() -> AsyncGenerator[MessagingApp, None]:
    # The Consumer Backend does not declare any queues, it just publishes messages
    async with with_messaging_app() as msg_app:
        yield msg_app


MessagingAppDep = Annotated[MessagingApp, Depends(get_messaging_app)]


def _read_public_key() -> str:
    """Read the public key from the certificate file specified by the
    EDC_CERT_PATH environment variable."""

    app_config: AppConfig = get_config()
    cert_path = app_config.cert_path

    if not cert_path:
        raise ValueError("EDC_CERT_PATH environment variable not set")

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

    try:
        public_key = _read_public_key()
    except:  # pylint: disable=bare-except
        _logger.warning("Could not read public key for JWT validation", exc_info=True)
        public_key = None

    decode_kwargs = {"algorithms": ["RS256"], "options": {"verify_signature": False}}

    if public_key:
        decode_kwargs = {
            **decode_kwargs,
            **{
                "key": public_key,
                "options": {"verify_signature": True},
            },
        }

    try:
        _logger.debug("Trying to decode JWT:\n%s", pprint.pformat(decode_kwargs))
        ret = jwt.decode(jwt=item.authCode, **decode_kwargs)
    except jwt.exceptions.InvalidSignatureError:
        _logger.warning("Invalid signature, trying to decode without signature")
        decode_kwargs["options"]["verify_signature"] = False
        ret = jwt.decode(jwt=item.authCode, **decode_kwargs)

    ret["dad"] = json.loads(ret["dad"])

    _logger.debug("Decoded JWT:\n%s", pprint.pformat(ret))

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
        contract_id=item.contractId,
    )

    # The provider hostname is included in the routing key to facilitate
    # the scenario of the consumer communicating with multiple providers in parallel.
    # The provider hostname is included in its slugified form since dots are
    # interpreted as routing key separators by RabbitMQ.
    routing_key = f"{BASE_HTTP_PULL_QUEUE_ROUTING_KEY}.{slugify(message.provider_host)}"

    _logger.info(
        "Publishing %s to routing key '%s'", message.__class__.__name__, routing_key
    )

    await messaging_app.broker.publish(
        message=message,
        routing_key=routing_key,
        exchange=messaging_app.exchange,
    )

    return {
        "broker": str(messaging_app.broker),
        "exchange": str(messaging_app.exchange),
    }


async def _http_push_endpoint(
    body: dict, routing_key: str, messaging_app: MessagingApp
) -> dict:
    _logger.debug("Received HTTP Push request:\n%s", pprint.pformat(body))
    message = HttpPushMessage(body=body)

    _logger.info(
        "Publishing %s to routing key '%s'", message.__class__.__name__, routing_key
    )

    await messaging_app.broker.publish(
        message=message,
        routing_key=routing_key,
        exchange=messaging_app.exchange,
    )

    return {
        "broker": str(messaging_app.broker),
        "exchange": str(messaging_app.exchange),
    }


@app.post("/push")
async def http_push_endpoint(body: dict, messaging_app: MessagingAppDep):
    return await _http_push_endpoint(
        body=body,
        routing_key=BASE_HTTP_PUSH_QUEUE_ROUTING_KEY,
        messaging_app=messaging_app,
    )


@app.post("/push/{routing_key_parts:path}")
async def http_push_endpoint(
    body: dict, messaging_app: MessagingAppDep, routing_key_parts: str = ""
):  # pylint: disable=function-redefined
    parts = [item for item in routing_key_parts.split("/") if item]
    routing_key_suffix = "." + ".".join(parts) if len(parts) > 0 else ""
    routing_key = BASE_HTTP_PUSH_QUEUE_ROUTING_KEY + routing_key_suffix

    return await _http_push_endpoint(
        body=body, routing_key=routing_key, messaging_app=messaging_app
    )


def run_server():
    """Run the HTTP server that exposes the HTTP API backend."""

    log_level = os.environ.get("LOG_LEVEL", "DEBUG")
    coloredlogs.install(level=log_level)
    app_config = get_config()
    port = app_config.http_api_port
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level.lower())
