import json
import logging
import pprint
from dataclasses import dataclass
from typing import Union

from propan import PropanApp, RabbitBroker
from propan.brokers.rabbit import ExchangeType, RabbitExchange, RabbitQueue
from pydantic import BaseModel

from edcpy.config import AppConfig

HTTP_PULL_QUEUE_ROUTING_KEY = "http.pull"
HTTP_PUSH_QUEUE_ROUTING_KEY = "http.push"
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

    @property
    def http_method(self) -> str:
        ret = (
            self.auth_code_decoded.get("dad", {})
            .get("properties", {})
            .get("method", None)
        )

        assert ret is not None, "Could not find HTTP method in auth code"

        return ret

    @property
    def request_args(self) -> dict:
        return {
            "method": self.http_method,
            "url": self.endpoint,
            "headers": {self.auth_key: self.auth_code},
        }


class HttpPushMessage(BaseModel):
    body: dict


@dataclass
class MessagingApp:
    broker: RabbitBroker
    app: PropanApp
    exchange: RabbitExchange


async def start_messaging_app(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    http_pull_queue_name: str = DEFAULT_HTTP_PULL_QUEUE_NAME,
    http_push_queue_name: str = DEFAULT_HTTP_PUSH_QUEUE_NAME,
    http_pull_handler: Union[callable, None] = None,
    http_push_handler: Union[callable, None] = None,
) -> MessagingApp:
    rabbit_url = AppConfig.from_environ().rabbit_url
    assert rabbit_url, "RabbitMQ URL is not set"

    _logger.info(f"Connecting to RabbitMQ at {rabbit_url}")
    broker = RabbitBroker(rabbit_url, logger=_logger)
    app = PropanApp(broker, logger=_logger)

    _logger.info(f"Declaring exchange {exchange_name}")

    topic_exchange = RabbitExchange(
        exchange_name,
        auto_delete=False,
        passive=False,
        internal=False,
        robust=True,
        type=ExchangeType.TOPIC,
    )

    _logger.info(f"Declaring queue {http_pull_queue_name}")

    http_pull_queue = RabbitQueue(
        http_pull_queue_name,
        auto_delete=False,
        exclusive=False,
        passive=False,
        robust=True,
        routing_key=HTTP_PULL_QUEUE_ROUTING_KEY,
    )

    if http_pull_handler is not None:
        broker.handle(http_pull_queue, topic_exchange)(http_pull_handler)

    _logger.info(f"Declaring queue {http_push_queue_name}")

    http_push_queue = RabbitQueue(
        http_push_queue_name,
        auto_delete=False,
        exclusive=False,
        passive=False,
        robust=True,
        routing_key=HTTP_PUSH_QUEUE_ROUTING_KEY,
    )

    if http_push_handler is not None:
        broker.handle(http_push_queue, topic_exchange)(http_push_handler)

    _logger.info("Starting broker")
    await broker.start()

    return MessagingApp(broker=broker, app=app, exchange=topic_exchange)
