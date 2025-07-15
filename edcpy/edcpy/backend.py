import json
import logging
import os
import pprint
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Literal, Optional, Union

import coloredlogs
import jwt
import uvicorn
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from slugify import slugify
from typing_extensions import Annotated, AsyncGenerator

from edcpy.config import AppConfig, get_config
from edcpy.messaging import (
    BASE_HTTP_PULL_QUEUE_ROUTING_KEY,
    BASE_HTTP_PUSH_QUEUE_ROUTING_KEY,
    HttpPullMessage,
    HttpPushMessage,
    MessagingApp,
    MessagingClient,
    start_publisher_messaging_app,
)

_logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_api_key() -> str:
    """Get API key from environment variable."""

    api_key = os.environ.get("API_AUTH_KEY")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "API_AUTH_KEY environment variable is not set. "
                "SSE endpoints require this to prevent unauthorized data access. "
                "Please set API_AUTH_KEY in the environment to enable SSE endpoints."
            ),
        )

    return api_key


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify API key from Authorization header."""

    api_key = get_api_key()

    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown of the messaging app."""

    _logger.info("Starting up messaging app...")

    messaging_app = await start_publisher_messaging_app()
    app.state.messaging_app = messaging_app

    _logger.info("Messaging app started successfully")

    yield

    _logger.info("Shutting down messaging app...")

    try:
        await messaging_app.broker.close()
        _logger.info("Messaging app shut down successfully")
    except Exception:
        _logger.warning("Could not close messaging app broker", exc_info=True)


app = FastAPI(lifespan=lifespan)


class EndpointDataReference(BaseModel):
    """
    Data structure representing a reference to a data transfer endpoint
    in the EDC (Eclipse Dataspace Connector) framework.
    """

    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: Dict[str, Any]
    contractId: str


class SSEPullMessage(BaseModel):
    """
    Pydantic model for SSE pull transfer message data.

    This model represents the structure of data sent via Server-Sent Events
    when streaming HttpPullMessage objects to browser clients.
    """

    type: Literal["pull_message"] = "pull_message"
    transfer_process_id: str = Field(..., description="EDC transfer process ID")
    request_args: Dict[str, Any] = Field(
        ..., description="HTTP request arguments for the provider"
    )
    auth_code: str = Field(..., description="JWT authentication code")
    auth_key: str = Field(..., description="Authentication key header name")
    endpoint: str = Field(..., description="Provider data endpoint URL")
    properties: Dict[str, Any] = Field(
        ..., description="Additional transfer properties"
    )
    contract_id: str = Field(..., description="EDC contract ID")


class SSEPushMessage(BaseModel):
    """
    Pydantic model for SSE push transfer message data.

    This model represents the structure of data sent via Server-Sent Events
    when streaming HttpPushMessage objects to browser clients.
    """

    type: Literal["push_message"] = "push_message"
    routing_path: str = Field(..., description="Message routing path")
    body: Any = Field(..., description="Message body data from provider")


class SSEErrorMessage(BaseModel):
    """
    Pydantic model for SSE error message data.

    This model represents the structure of error messages sent via Server-Sent Events
    when streaming operations encounter errors.
    """

    type: Literal["error"] = "error"
    message: str = Field(..., description="Error message description")
    transfer_process_id: Optional[str] = Field(
        None, description="Transfer process ID if applicable"
    )
    routing_path: Optional[str] = Field(None, description="Routing path if applicable")


class SSEStreamParams(BaseModel):
    """
    Pydantic model for SSE stream query parameters.

    This model validates and documents the query parameters accepted by SSE endpoints.
    """

    timeout: int = Field(60, ge=1, le=3600, description="Timeout in seconds (1-3600)")
    provider_host: Optional[str] = Field(
        None, description="Provider hostname for pull operations"
    )


class BrokerResponse(BaseModel):
    """
    Pydantic model for broker response data.

    This model represents the response structure returned by HTTP endpoints
    that publish messages to the RabbitMQ broker.
    """

    broker: str = Field(..., description="Broker connection string")
    exchange: str = Field(..., description="RabbitMQ exchange name")


def get_messaging_app(request: Request) -> MessagingApp:
    """Get the messaging app instance from application state."""

    return request.app.state.messaging_app


MessagingAppDep = Annotated[MessagingApp, Depends(get_messaging_app)]


def _read_public_key() -> bytes:
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


def _decode_auth_code(item: EndpointDataReference) -> Dict[str, Any]:
    """Decode the EndpointDataReference element received from the data space."""

    try:
        public_key = _read_public_key()
    except Exception:
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
) -> BrokerResponse:
    """Handle HTTP Pull requests by publishing them to RabbitMQ.
    The message is published with a routing key that includes the provider hostname
    to support parallel communication with multiple providers."""

    _logger.debug(
        "Received HTTP Pull request %s:\n%s",
        EndpointDataReference,
        pprint.pformat(item.dict()),
    )

    decoded_auth_code = _decode_auth_code(item)

    # message.id is the transfer process ID
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
    routing_key_parts = [
        BASE_HTTP_PULL_QUEUE_ROUTING_KEY,
        slugify(message.provider_host),
        slugify(message.id),
    ]

    routing_key = ".".join(routing_key_parts)

    _logger.info(
        "Publishing %s to routing key '%s'", message.__class__.__name__, routing_key
    )

    await messaging_app.broker.publish(
        message=message,
        routing_key=routing_key,
        exchange=messaging_app.exchange,
    )

    return BrokerResponse(
        broker=str(messaging_app.broker),
        exchange=str(messaging_app.exchange),
    )


async def _http_push_endpoint(
    body: Union[Dict[str, Any], str], routing_key: str, messaging_app: MessagingApp
) -> BrokerResponse:
    """Internal helper to handle HTTP Push requests by publishing them to RabbitMQ.
    Used by both the basic push endpoint and the routing-key-specific endpoint."""

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

    return BrokerResponse(
        broker=str(messaging_app.broker),
        exchange=str(messaging_app.exchange),
    )


@app.post("/push")
async def http_push_endpoint(
    body: Dict[str, Any], messaging_app: MessagingAppDep
) -> BrokerResponse:
    """Handle basic HTTP Push requests by publishing them to RabbitMQ using the default routing key."""

    return await _http_push_endpoint(
        body=body,
        routing_key=BASE_HTTP_PUSH_QUEUE_ROUTING_KEY,
        messaging_app=messaging_app,
    )


@app.post("/push/{routing_key_parts:path}")
async def http_push_endpoint_with_routing_key(
    request: Request, messaging_app: MessagingAppDep, routing_key_parts: str = ""
) -> BrokerResponse:
    """Handle HTTP Push requests with custom routing keys.
    The routing key parts from the URL path are appended to the base routing key."""

    body_bytes = await request.body()

    try:
        body = await request.json()
    except Exception:
        body = body_bytes.decode()

    parts = [item for item in routing_key_parts.split("/") if item]
    routing_key_suffix = "." + ".".join(parts) if len(parts) > 0 else ""
    routing_key = BASE_HTTP_PUSH_QUEUE_ROUTING_KEY + routing_key_suffix

    return await _http_push_endpoint(
        body=body, routing_key=routing_key, messaging_app=messaging_app
    )


async def _stream_pull_messages(
    transfer_process_id: str, timeout: int = 60, provider_host: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Stream HttpPullMessage objects as SSE for a specific transfer process ID."""

    # Use a unique consumer ID for each SSE connection to avoid conflicts
    consumer_id = f"sse-pull-{transfer_process_id}-{uuid.uuid4().hex[:8]}"
    client = MessagingClient(consumer_id)

    try:
        # Create an exclusive queue that will be automatically deleted when the connection closes
        async with client.pull_consumer(
            timeout=timeout,
            provider_host=provider_host,
            auto_delete=True,
        ) as consumer:
            async with consumer.wait_for_message(
                expected_id=transfer_process_id, timeout=timeout
            ) as http_pull_message:
                message_data = SSEPullMessage(
                    transfer_process_id=transfer_process_id,
                    request_args=http_pull_message.request_args,
                    auth_code=http_pull_message.auth_code,
                    auth_key=http_pull_message.auth_key,
                    endpoint=http_pull_message.endpoint,
                    properties=http_pull_message.properties,
                    contract_id=http_pull_message.contract_id,
                )

                yield f"data: {message_data.model_dump_json()}\n\n"
    except Exception as e:
        error_data = SSEErrorMessage(
            message=str(e),
            transfer_process_id=transfer_process_id,
            routing_path=None,
        )

        yield f"data: {error_data.model_dump_json()}\n\n"


async def _stream_push_messages(
    routing_path: str, timeout: int = 60
) -> AsyncGenerator[str, None]:
    """Stream HttpPushMessage objects as SSE for a specific routing path."""

    # Use a unique consumer ID for each SSE connection to avoid conflicts
    consumer_id = f"sse-push-{routing_path.replace('/', '-')}-{uuid.uuid4().hex[:8]}"
    client = MessagingClient(consumer_id)

    try:
        # Create an exclusive queue that will be automatically deleted when the connection closes
        async with client.push_consumer(
            routing_path=routing_path,
            timeout=timeout,
            auto_delete=True,
        ) as consumer:
            async with consumer.wait_for_message(timeout=timeout) as http_push_message:
                message_data = SSEPushMessage(
                    routing_path=routing_path,
                    body=http_push_message.body,
                )

                yield f"data: {message_data.model_dump_json()}\n\n"
    except Exception as e:
        error_data = SSEErrorMessage(
            message=str(e),
            transfer_process_id=None,
            routing_path=routing_path,
        )

        yield f"data: {error_data.model_dump_json()}\n\n"


@app.get("/pull/stream/{transfer_process_id}")
async def stream_pull_messages(
    transfer_process_id: str,
    params: SSEStreamParams = Depends(),
    api_key: str = Depends(verify_api_key),
) -> StreamingResponse:
    """Stream HttpPullMessage objects as Server-Sent Events for browser consumption.

    This endpoint allows browsers to receive pull transfer credentials in real-time
    without requiring AMQP support. The browser can then use the credentials to
    make direct HTTP requests to the provider's data endpoints."""

    _logger.info(
        "Starting SSE stream for pull transfer process: %s (timeout: %ds)",
        transfer_process_id,
        params.timeout,
    )

    return StreamingResponse(
        _stream_pull_messages(
            transfer_process_id=transfer_process_id,
            timeout=params.timeout,
            provider_host=params.provider_host,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@app.get("/push/stream/{routing_key_parts:path}")
async def stream_push_messages(
    routing_key_parts: str,
    params: SSEStreamParams = Depends(),
    api_key: str = Depends(verify_api_key),
) -> StreamingResponse:
    """Stream HttpPushMessage objects as Server-Sent Events for browser consumption.

    This endpoint allows browsers to receive push transfer data in real-time
    without requiring AMQP support. The provider sends data to the backend
    which then streams it to the browser via SSE."""

    _logger.info(
        "Starting SSE stream for push routing path: %s (timeout: %ds)",
        routing_key_parts,
        params.timeout,
    )

    return StreamingResponse(
        _stream_push_messages(
            routing_path=routing_key_parts,
            timeout=params.timeout,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


def run_server():
    """Run the HTTP server that exposes the HTTP API backend."""

    log_level = os.environ.get("LOG_LEVEL", "DEBUG")
    coloredlogs.install(level=log_level)
    app_config = get_config()
    port = app_config.http_api_port
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level.lower())
