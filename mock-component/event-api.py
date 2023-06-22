import asyncio
import json
import logging
import os
import random

import coloredlogs
from propan import PropanApp, RabbitBroker
from propan.brokers.rabbit import RabbitExchange, RabbitQueue
from pydantic import BaseModel

coloredlogs.install(level=logging.INFO)
_logger = logging.getLogger(__name__)

broker = RabbitBroker(os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"))
app = PropanApp(broker, logger=_logger)

exchange = RabbitExchange("tasks-exchange", auto_delete=True)
task_queue = RabbitQueue("aggregation-task-queue", auto_delete=True)


class ConsumptionAggregationTaskMessage(BaseModel):
    location: str
    sink_url: str


@broker.handle(task_queue, exchange)
async def aggregation_handler(body: ConsumptionAggregationTaskMessage):
    """Handler that listens for messages that act as triggers for long-running
    tasks that compute aggregated electricity consumption datasets."""

    _logger.info("Received electricity consumption aggregation task: %s", body)
    sleep_time = random.random() * 5 + random.randint(1, 5)
    _logger.info("Waiting for %s secs to simulate long-running task", sleep_time)
    await asyncio.sleep(sleep_time)

    _logger.info(
        "Completed long-running task to compute aggregated electricity consumption: %s",
        body,
    )
