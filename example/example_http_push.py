"""
An example of the Provider Push use case from the Transfer Data Plane extension:
https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane.

In this case the Provider calls the Mock HTTP API contained in the 
'mock-component' folder and then 'pushes' the result to the Consumer Backend.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pprint

import coloredlogs

from edcpy.config import ConsumerProviderPairConfig
from edcpy.messaging import HttpPushMessage, messaging_app
from edcpy.orchestrator import RequestOrchestrator

_ASSET_CONSUMPTION = "GET-consumption"

_CONSUMER_BACKEND_BASE_URL = "http://consumer.local:8000"
_CONSUMER_BACKEND_PUSH_PATH = "/push"
_CONSUMER_BACKEND_PUSH_METHOD = "POST"

_QUEUE_GET_TIMEOUT_SECS = 10

_logger = logging.getLogger(__name__)


async def push_handler(message: dict, queue: asyncio.Queue):
    # Using type hints for the message argument seems to break in Python 3.8.
    message = HttpPushMessage(**message)

    _logger.info(
        "Putting HTTP Push request into the queue:\n%s", pprint.pformat(message.dict())
    )

    await queue.put(message)


async def main():
    queue: asyncio.Queue[HttpPushMessage] = asyncio.Queue()

    async def push_handler_partial(message: dict):
        await push_handler(message=message, queue=queue)

    # Start the Rabbit broker and set the handler for the HTTP push messages
    # received on the Consumer Backend from the Provider.
    async with messaging_app(http_push_handler=push_handler_partial):
        # The orchestrator contains the logic to interact with the EDC HTTP APIs.
        # https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api/0.1.0-SNAPSHOT
        config = ConsumerProviderPairConfig.from_env()
        orchestrator = RequestOrchestrator(config=config)
        _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

        # Initiate the transfer processfor the asset.
        transfer_details = await orchestrator.prepare_to_transfer_asset(
            asset_query=_ASSET_CONSUMPTION
        )

        # sink_base_url, sink_path and sink_method are the details of our local Consumer Backend.
        # Multiple path parameters can be added after the base path to be added to the routing key.
        sink_path = f"{_CONSUMER_BACKEND_PUSH_PATH}/specific/routing/key"

        transfer_process = await orchestrator.create_provider_push_transfer_process(
            contract_agreement_id=transfer_details.contract_agreement_id,
            asset_id=transfer_details.asset_id,
            sink_base_url=_CONSUMER_BACKEND_BASE_URL,
            sink_path=sink_path,
            sink_method=_CONSUMER_BACKEND_PUSH_METHOD,
        )

        transfer_process_id = transfer_process["@id"]

        await orchestrator.wait_for_transfer_process(
            transfer_process_id=transfer_process_id
        )

        # Wait for the message published by the Consumer Backend to the Rabbit broker.
        # The message contains the response from the Mock HTTP API without any modification.
        # That is, the message has been 'pushed' from the Provider to the Consumer Backend.
        http_push_msg = await asyncio.wait_for(
            queue.get(), timeout=_QUEUE_GET_TIMEOUT_SECS
        )

        _logger.info(
            "Received response from Mock HTTP API:\n%s",
            pprint.pformat(http_push_msg.body),
        )


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv("LOG_LEVEL", "DEBUG"))
    asyncio.run(main())
