import json
import logging
import pprint
from dataclasses import dataclass

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
    auth_code: dict
    auth_code_encoded: str
    auth_key: str
    endpoint: str
    id: str
    properties: dict

    @property
    def http_method(self) -> str:
        source_json_dad = (
            self.auth_code.get("dad", {})
            .get("properties", {})
            .get("authCode", {})
            .get("dad")
        )

        try:
            props = json.loads(source_json_dad)["properties"]
            return next(val for key, val in props.items() if key.endswith("method"))
        except:
            raise Exception("Failed to parse HTTP method from decoded auth code")


async def default_pull_handler(message: HttpPullMessage):
    _logger.warning("Unhandled HTTP Pull request:\n%s", pprint.pformat(message.dict()))


class HttpPushMessage(BaseModel):
    body: dict


async def default_push_handler(message: HttpPushMessage):
    _logger.warning("Unhandled HTTP Push request:\n%s", pprint.pformat(message.dict()))


@dataclass
class MessagingApp:
    broker: RabbitBroker
    app: PropanApp
    exchange: RabbitExchange


async def start_messaging_app(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    http_pull_queue_name: str = DEFAULT_HTTP_PULL_QUEUE_NAME,
    http_push_queue_name: str = DEFAULT_HTTP_PUSH_QUEUE_NAME,
    http_pull_handler: callable = default_pull_handler,
    http_push_handler: callable = default_push_handler,
) -> MessagingApp:
    rabbit_url = AppConfig.from_environ().rabbit_url
    assert rabbit_url, "RabbitMQ URL is not set"

    _logger.info(f"Connecting to RabbitMQ at {rabbit_url}")
    broker = RabbitBroker(rabbit_url, logger=_logger)
    app = PropanApp(broker, logger=_logger)

    _logger.info(f"Declaring exchange {exchange_name}")

    topic_exchange = RabbitExchange(
        exchange_name, auto_delete=True, type=ExchangeType.TOPIC
    )

    _logger.info(f"Declaring queue {http_pull_queue_name}")

    http_pull_queue = RabbitQueue(
        http_pull_queue_name,
        auto_delete=True,
        routing_key=HTTP_PULL_QUEUE_ROUTING_KEY,
    )

    broker.handle(http_pull_queue, topic_exchange)(http_pull_handler)

    _logger.info(f"Declaring queue {http_push_queue_name}")

    http_push_queue = RabbitQueue(
        http_push_queue_name,
        auto_delete=True,
        routing_key=HTTP_PUSH_QUEUE_ROUTING_KEY,
    )

    broker.handle(http_push_queue, topic_exchange)(http_push_handler)

    _logger.info("Starting broker")
    await broker.start()

    return MessagingApp(broker=broker, app=app, exchange=topic_exchange)
