import logging
from dataclasses import dataclass

from propan import PropanApp, RabbitBroker
from propan.brokers.rabbit import ExchangeType, RabbitExchange, RabbitQueue

from edcpy.config import AppConfig

HTTP_PULL_QUEUE_NAME = "http.pull.*"
DEFAULT_EXCHANGE_NAME = "edcpy-topic-exchange"
DEFAULT_HTTP_PULL_QUEUE_NAME = "http-pull-queue"

_logger = logging.getLogger(__name__)


@dataclass
class MessagingApp:
    broker: RabbitBroker
    app: PropanApp


async def http_pull_handler():
    pass


async def start_messaging_app(
    exchange_name: str = DEFAULT_EXCHANGE_NAME,
    http_pull_queue_name: str = DEFAULT_HTTP_PULL_QUEUE_NAME,
) -> MessagingApp:
    rabbit_url = AppConfig.from_environ().rabbit_url
    assert rabbit_url, "RabbitMQ URL is not set"

    _logger.info(f"Connecting to RabbitMQ at {rabbit_url}")
    broker = RabbitBroker(rabbit_url)
    app = PropanApp(broker)

    _logger.info(f"Declaring exchange {exchange_name}")

    topic_exchange = RabbitExchange(
        exchange_name, auto_delete=True, type=ExchangeType.TOPIC
    )

    _logger.info(f"Declaring queue {http_pull_queue_name}")

    http_pull_queue = RabbitQueue(
        http_pull_queue_name, auto_delete=True, routing_key=HTTP_PULL_QUEUE_NAME
    )

    broker.handle(http_pull_queue, topic_exchange)

    return MessagingApp(broker=broker, app=app)
