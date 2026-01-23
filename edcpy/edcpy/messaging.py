import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Callable, List, Optional, Tuple, cast
from urllib.parse import urlparse

import inspect

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs
from pydantic import BaseModel
from slugify import slugify

from edcpy.config import AppConfig, get_config
from edcpy.message_handler import (
    MessageConsumer,
    create_handler_function,
    create_message_handler,
)

BASE_HTTP_PULL_QUEUE_ROUTING_KEY = "http.pull"
BASE_HTTP_PUSH_QUEUE_ROUTING_KEY = "http.push"
DEFAULT_EXCHANGE_NAME = "edcpy-topic-exchange"
DEFAULT_X_MESSAGE_TTL = 15 * 60 * 1000  # 15 minutes
DEFAULT_X_EXPIRES = 15 * 60 * 1000  # 15 minutes

_logger = logging.getLogger(__name__)


class QueueType(str, Enum):
    """Enumeration of supported queue types."""

    PULL = "pull"
    PUSH = "push"


@dataclass
class ConsumerQueueConfig:
    """Configuration for consumer-specific queues with RabbitMQ cleanup features."""

    queue_name: str
    routing_key: str
    consumer_id: str
    queue_type: QueueType
    auto_delete: bool = True
    exclusive: bool = False
    # Message TTL controls how long messages stay in a queue before expiring (milliseconds)
    x_message_ttl: Optional[int] = None
    # Queue TTL determines how long an unused queue exists before deletion (milliseconds)
    x_expires: Optional[int] = None


class ConsumerQueueFactory:
    """Factory for creating consumer-specific queues with proper routing and cleanup features."""

    def __init__(self, exchange_name: str = DEFAULT_EXCHANGE_NAME):
        """Initialize the ConsumerQueueFactory."""

        self.exchange_name = exchange_name

    def create_queue_config(
        self,
        queue_type: QueueType,
        consumer_id: Optional[str] = None,
        provider_host: Optional[str] = None,
        routing_path: Optional[str] = None,
        transfer_process_id: Optional[str] = None,
        auto_delete: bool = True,
        exclusive: bool = False,
        x_message_ttl: Optional[int] = DEFAULT_X_MESSAGE_TTL,
        x_expires: Optional[int] = DEFAULT_X_EXPIRES,
    ) -> ConsumerQueueConfig:
        """Create a queue configuration for HTTP operations with automatic cleanup.

        Args:
            queue_type: QueueType.PULL or QueueType.PUSH
            consumer_id: Unique identifier for the consumer (auto-generated if None)
            provider_host: Provider hostname for pull operations
            routing_path: Routing path for push operations
            transfer_process_id: Specific transfer process ID
            auto_delete: Whether to auto-delete the queue when consumer disconnects
            exclusive: Whether the queue is exclusive to this connection

        Returns:
            ConsumerQueueConfig with appropriate routing and cleanup settings
        """

        if not isinstance(queue_type, QueueType):
            raise TypeError(
                f"queue_type must be a QueueType enum, got {type(queue_type)}"
            )

        if consumer_id is None:
            consumer_id = f"{queue_type}-consumer-{uuid.uuid4().hex[:8]}"

        routing_key = self._build_routing_key(
            queue_type, provider_host, routing_path, transfer_process_id
        )

        queue_name = f"{queue_type.value}-{consumer_id}"

        _logger.info(
            "Creating queue config for %s consumer '%s' with routing key '%s'",
            queue_type,
            consumer_id,
            routing_key,
        )

        return ConsumerQueueConfig(
            queue_name=queue_name,
            routing_key=routing_key,
            consumer_id=consumer_id,
            queue_type=queue_type,
            auto_delete=auto_delete,
            exclusive=exclusive,
            x_message_ttl=x_message_ttl,
            x_expires=x_expires,
        )

    def _build_routing_key(
        self,
        queue_type: QueueType,
        provider_host: Optional[str],
        routing_path: Optional[str],
        transfer_process_id: Optional[str],
    ) -> str:
        """Build routing key for the specified queue type and parameters."""

        if queue_type == QueueType.PULL:
            return self._build_pull_routing_key(provider_host, transfer_process_id)
        elif queue_type == QueueType.PUSH:
            return self._build_push_routing_key(routing_path)
        else:
            raise ValueError(f"Invalid queue type: {queue_type}")

    def _build_pull_routing_key(
        self, provider_host: Optional[str], transfer_process_id: Optional[str]
    ) -> str:
        """Build routing key for pull operations."""

        routing_key_parts = [BASE_HTTP_PULL_QUEUE_ROUTING_KEY]

        if not provider_host:
            routing_key_parts.append("#")
        else:
            routing_key_parts.append(slugify(provider_host))
            routing_key_parts.append(transfer_process_id or "*")

        return ".".join(routing_key_parts)

    def _build_push_routing_key(self, routing_path: Optional[str]) -> str:
        """Build routing key for push operations."""

        routing_key_parts = [BASE_HTTP_PUSH_QUEUE_ROUTING_KEY]

        if not routing_path:
            routing_key_parts.append("#")
        else:
            path_parts = [part for part in routing_path.split("/") if part]
            routing_key_parts.extend(path_parts)

        return ".".join(routing_key_parts)

    def create_pull_queue_config(
        self,
        consumer_id: Optional[str] = None,
        provider_host: Optional[str] = None,
        transfer_process_id: Optional[str] = None,
        auto_delete: bool = True,
        exclusive: bool = False,
        x_message_ttl: Optional[int] = DEFAULT_X_MESSAGE_TTL,
        x_expires: Optional[int] = DEFAULT_X_EXPIRES,
    ) -> ConsumerQueueConfig:
        """Create a queue configuration for HTTP pull operations."""

        return self.create_queue_config(
            queue_type=QueueType.PULL,
            consumer_id=consumer_id,
            provider_host=provider_host,
            transfer_process_id=transfer_process_id,
            auto_delete=auto_delete,
            exclusive=exclusive,
            x_message_ttl=x_message_ttl,
            x_expires=x_expires,
        )

    def create_push_queue_config(
        self,
        consumer_id: Optional[str] = None,
        routing_path: Optional[str] = None,
        auto_delete: bool = True,
        exclusive: bool = False,
        x_message_ttl: Optional[int] = DEFAULT_X_MESSAGE_TTL,
        x_expires: Optional[int] = DEFAULT_X_EXPIRES,
    ) -> ConsumerQueueConfig:
        """Create a queue configuration for HTTP push operations."""

        return self.create_queue_config(
            queue_type=QueueType.PUSH,
            consumer_id=consumer_id,
            routing_path=routing_path,
            auto_delete=auto_delete,
            exclusive=exclusive,
            x_message_ttl=x_message_ttl,
            x_expires=x_expires,
        )


class HttpPullMessage(BaseModel):
    """Represents a message for HTTP pull operations."""

    auth_code_decoded: dict
    auth_code: str
    auth_key: str
    endpoint: str
    id: str
    properties: dict
    contract_id: str

    @property
    def http_method(self) -> str:
        """Extract HTTP method from the decoded auth code."""

        ret = (
            self.auth_code_decoded.get("dad", {})
            .get("properties", {})
            .get("method", None)
        )

        if ret is None:
            raise ValueError("Could not find HTTP method in auth code")

        return ret

    @property
    def request_args(self) -> dict:
        """Build request arguments for HTTP call."""

        return {
            "method": self.http_method,
            "url": self.endpoint,
            "headers": {self.auth_key: self.auth_code},
            "params": {"contractId": self.contract_id},
        }

    @property
    def transfer_process_id(self) -> str:
        """Return the transfer process ID."""

        return self.id

    @property
    def provider_host(self):
        """Extract the provider host from the endpoint URL."""

        parsed = urlparse(self.endpoint)
        return parsed.netloc.split(":")[0]


class HttpPushMessage(BaseModel):
    """Represents a message for HTTP push operations."""

    body: Any


@dataclass
class MessagingApp:
    """Container for messaging app components."""

    broker: RabbitBroker
    app: FastStream
    exchange: RabbitExchange
    consumer_queues: Optional[List[RabbitQueue]] = None

    def __post_init__(self):

        if self.consumer_queues is None:
            self.consumer_queues = []


@asynccontextmanager
async def _create_messaging_app_base(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    config: Optional[AppConfig] = None,
) -> AsyncGenerator[Tuple[RabbitBroker, FastStream, RabbitExchange], None]:
    """Create the base messaging app components."""

    app_config: AppConfig = config or get_config()
    rabbit_url = app_config.rabbit_url

    if not rabbit_url:
        raise ValueError("RabbitMQ URL is not set")

    _logger.info("Starting messaging app")

    broker = RabbitBroker(rabbit_url, logger=_logger)
    app = FastStream(broker, logger=_logger)

    topic_exchange = _create_rabbit_exchange(exchange_name)

    yield broker, app, topic_exchange

    await broker.start()
    _logger.info("Started broker")

    await broker.declare_exchange(topic_exchange)
    _logger.info("Exchange '%s' declared", exchange_name)


async def _create_messaging_app_consumer(
    queue_config: ConsumerQueueConfig,
    handler: Callable,
    config: Optional[AppConfig] = None,
) -> Tuple[RabbitBroker, FastStream, RabbitExchange, RabbitQueue]:
    """Create and configure a consumer-specific queue with RabbitMQ cleanup features."""

    queue_arguments = {}

    if queue_config.x_message_ttl is not None:
        queue_arguments["x-message-ttl"] = queue_config.x_message_ttl

    if queue_config.x_expires is not None:
        queue_arguments["x-expires"] = queue_config.x_expires

    queue = RabbitQueue(
        queue_config.queue_name,
        auto_delete=queue_config.auto_delete,
        exclusive=queue_config.exclusive,
        durable=not queue_config.auto_delete,
        routing_key=queue_config.routing_key,
        arguments=cast(ClassicQueueArgs, queue_arguments),
    )

    broker = None
    app = None
    exchange = None

    async with _create_messaging_app_base(config=config) as (broker, app, exchange):
        # Always use manual acknowledgment for consumer queues
        # The subscriber must be created before the broker starts—this is why we use a context manager here
        broker.subscriber(queue=queue, exchange=exchange, no_ack=False)(handler)

    # Declare the queue using FastStream
    await broker.declare_queue(queue)

    _logger.info(
        "Created consumer queue '%s' with routing key '%s' and cleanup features: Auto-delete=%s, Exclusive=%s, Durable=%s",
        queue_config.queue_name,
        queue_config.routing_key,
        queue_config.auto_delete,
        queue_config.exclusive,
        not queue_config.auto_delete,
    )

    _logger.info("Attached handler to consumer queue '%s'", queue_config.queue_name)

    return broker, app, exchange, queue


async def start_publisher_messaging_app(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    config: Optional[AppConfig] = None,
) -> MessagingApp:
    """Start a messaging app optimized for publishing messages only.

    Creates only the essential components needed for message publishing:
    broker connection and topic exchange. No queues are created.
    """

    async with _create_messaging_app_base(exchange_name, config=config) as (
        broker,
        app,
        exchange,
    ):
        pass

    _logger.info("Publisher messaging app started (no queues created)")

    return MessagingApp(
        broker=broker,
        app=app,
        exchange=exchange,
        consumer_queues=[],
    )


async def start_consumer_messaging_app(
    queue_config: ConsumerQueueConfig,
    handler: Callable,
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    config: Optional[AppConfig] = None,
) -> MessagingApp:
    """Start a messaging app with a consumer-specific queue."""

    broker, app, exchange, consumer_queue = await _create_messaging_app_consumer(
        queue_config=queue_config,
        handler=handler,
        config=config,
    )

    return MessagingApp(
        broker=broker,
        app=app,
        exchange=exchange,
        consumer_queues=[consumer_queue],
    )


def _create_rabbit_exchange(exchange_name: str) -> RabbitExchange:
    """Create a RabbitExchange with compatibility across faststream versions."""

    kwargs = {
        "auto_delete": False,
        "robust": True,
        "type": ExchangeType.TOPIC,
    }

    if "passive" in inspect.signature(RabbitExchange).parameters:
        kwargs["passive"] = False

    return RabbitExchange(exchange_name, **kwargs)


@asynccontextmanager
async def with_consumer_messaging_app(
    queue_config: ConsumerQueueConfig,
    handler: Callable,
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    config: Optional[AppConfig] = None,
) -> AsyncGenerator[MessagingApp, None]:
    """Context manager for a consumer-specific messaging app.

    Sets up a dedicated RabbitMQ queue for a consumer with the provided handler
    and ensures proper cleanup of resources when the context exits.

    Queue cleanup behavior:
    - auto_delete=True: Queue deleted when last consumer disconnects
    - auto_delete=False: Queue persists after consumers disconnect
    - exclusive=True: Queue tied to connection and deleted when connection closes

    Always uses manual message acknowledgment for reliable processing.
    """

    messaging_app: Optional[MessagingApp] = None

    try:
        messaging_app = await start_consumer_messaging_app(
            queue_config=queue_config,
            handler=handler,
            exchange_name=exchange_name,
            config=config,
        )

        yield messaging_app
    finally:
        if messaging_app is None:
            return
        try:
            await messaging_app.broker.close()
            _logger.debug("Closed consumer messaging app broker")
        except Exception:
            _logger.warning(
                "Could not close consumer messaging app broker", exc_info=True
            )


class MessagingClient:
    """Simplified client for messaging operations with automatic queue and handler management."""

    def __init__(
        self, consumer_id: Optional[str] = None, config: Optional[AppConfig] = None
    ):
        """Initialize the messaging client.

        Args:
            consumer_id: Unique identifier for the consumer (auto-generated if None)
            config: Application configuration (uses environment config if None)
        """

        self.consumer_id = consumer_id or f"consumer-{uuid.uuid4().hex[:8]}"
        self.queue_factory = ConsumerQueueFactory()
        self.config: AppConfig = config or get_config()

    @asynccontextmanager
    async def pull_consumer(
        self,
        timeout: int = 60,
        provider_host: Optional[str] = None,
        exclusive: bool = False,
        auto_delete: bool = True,
    ):
        """Context manager for pull message consumption.

        Args:
            timeout: Default timeout for message operations
            provider_host: Provider hostname for pull operations
            exclusive: Whether the queue is exclusive to this connection
            auto_delete: Whether to auto-delete the queue when consumer disconnects

        Yields:
            MessageConsumer: Consumer instance for message operations
        """

        queue_config = self.queue_factory.create_pull_queue_config(
            consumer_id=self.consumer_id,
            provider_host=provider_host,
            exclusive=exclusive,
            auto_delete=auto_delete,
        )

        handler = create_message_handler(HttpPullMessage, auto_acknowledge=False)
        handler_func = create_handler_function(handler)

        async with with_consumer_messaging_app(
            queue_config, handler_func, config=self.config
        ):
            yield MessageConsumer(handler, timeout)

    @asynccontextmanager
    async def push_consumer(
        self,
        routing_path: Optional[str] = None,
        timeout: int = 60,
        exclusive: bool = False,
        auto_delete: bool = True,
    ):
        """Context manager for push message consumption.

        Args:
            routing_path: Routing path for push operations
            timeout: Default timeout for message operations
            exclusive: Whether the queue is exclusive to this connection
            auto_delete: Whether to auto-delete the queue when consumer disconnects

        Yields:
            MessageConsumer: Consumer instance for message operations
        """

        queue_config = self.queue_factory.create_push_queue_config(
            consumer_id=self.consumer_id,
            routing_path=routing_path,
            exclusive=exclusive,
            auto_delete=auto_delete,
        )

        handler = create_message_handler(HttpPushMessage, auto_acknowledge=False)
        handler_func = create_handler_function(handler)

        async with with_consumer_messaging_app(
            queue_config, handler_func, config=self.config
        ):
            yield MessageConsumer(handler, timeout)
