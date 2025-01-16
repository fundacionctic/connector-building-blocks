import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Union
from urllib.parse import urlparse

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from pydantic import BaseModel  # pylint: disable=no-name-in-module

from edcpy.config import AppConfig, get_config

BASE_HTTP_PULL_QUEUE_ROUTING_KEY = "http.pull"
BASE_HTTP_PUSH_QUEUE_ROUTING_KEY = "http.push"
DEFAULT_EXCHANGE_NAME = "edcpy-topic-exchange"
DEFAULT_HTTP_PULL_QUEUE_NAME = "http-pull-queue"
DEFAULT_HTTP_PUSH_QUEUE_NAME = "http-push-queue"

_logger = logging.getLogger(__name__)


class HttpPullMessage(BaseModel):
    auth_code_decoded: dict
    auth_code: str
    auth_key: str
    endpoint: str
    id: str
    properties: dict
    contract_id: str

    @property
    def http_method(self) -> str:
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
        return {
            "method": self.http_method,
            "url": self.endpoint,
            "headers": {self.auth_key: self.auth_code},
            "params": {"contractId": self.contract_id},
        }

    @property
    def transfer_process_id(self) -> str:
        return self.id

    @property
    def provider_host(self):
        parsed = urlparse(self.endpoint)
        return parsed.netloc.split(":")[0]


class HttpPushMessage(BaseModel):
    body: dict


@dataclass
class MessagingApp:
    broker: RabbitBroker
    app: FastStream
    exchange: RabbitExchange


async def start_messaging_app(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    http_pull_queue_name: str = DEFAULT_HTTP_PULL_QUEUE_NAME,
    http_push_queue_name: str = DEFAULT_HTTP_PUSH_QUEUE_NAME,
    http_pull_queue_routing_key: str = f"{BASE_HTTP_PULL_QUEUE_ROUTING_KEY}.#",
    http_push_queue_routing_key: str = f"{BASE_HTTP_PUSH_QUEUE_ROUTING_KEY}.#",
    http_pull_handler: Union[callable, None] = None,
    http_push_handler: Union[callable, None] = None,
) -> MessagingApp:
    app_config: AppConfig = get_config()
    rabbit_url = app_config.rabbit_url

    if not rabbit_url:
        raise ValueError("RabbitMQ URL is not set")

    _logger.info("Connecting to RabbitMQ at %s", rabbit_url)
    broker = RabbitBroker(rabbit_url, logger=_logger)
    app = FastStream(broker, logger=_logger)

    _logger.info("Declaring exchange: %s", exchange_name)

    topic_exchange = RabbitExchange(
        exchange_name,
        auto_delete=False,
        passive=False,
        robust=True,
        type=ExchangeType.TOPIC,
    )

    if http_pull_handler is not None:
        _logger.info("Declaring queue: %s", http_pull_queue_name)

        http_pull_queue = RabbitQueue(
            http_pull_queue_name,
            auto_delete=False,
            exclusive=False,
            passive=False,
            robust=True,
            routing_key=http_pull_queue_routing_key,
        )

        broker.subscriber(http_pull_queue, topic_exchange)(http_pull_handler)

    if http_push_handler is not None:
        _logger.info("Declaring queue: %s", http_push_queue_name)

        http_push_queue = RabbitQueue(
            http_push_queue_name,
            auto_delete=False,
            exclusive=False,
            passive=False,
            robust=True,
            routing_key=http_push_queue_routing_key,
        )

        broker.subscriber(http_push_queue, topic_exchange)(http_push_handler)

    _logger.info("Starting broker")
    await broker.start()

    return MessagingApp(broker=broker, app=app, exchange=topic_exchange)


@asynccontextmanager
async def with_messaging_app(*args, **kwargs) -> AsyncGenerator[MessagingApp, None]:
    try:
        msg_app = await start_messaging_app(*args, **kwargs)
        yield msg_app
    finally:
        try:
            await msg_app.broker.close()
            _logger.debug("Closed messaging app broker")
        except Exception:  # pylint: disable=broad-except
            _logger.warning("Could not close messaging app broker", exc_info=True)
