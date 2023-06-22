"""
An example of the Provider Push use case from the Transfer Data Plane extension:
https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane

In this case the Provider calls the Mock HTTP API contained in the 
'mock-component' folder and then 'pushes' the result to the Consumer Backend.
"""

import asyncio
import logging
import os
import pprint

import coloredlogs

from edcpy.config import ConsumerProviderPairConfig
from edcpy.messaging import HttpPushMessage, start_messaging_app
from edcpy.orchestrator import RequestOrchestrator

_ASSET_CONSUMPTION = "GET-consumption"

_SINK_BASE_URL = "http://consumer.local:8000"
_SINK_PATH = "/push"
_SINK_METHOD = "POST"

_logger = logging.getLogger(__name__)
_queue: asyncio.Queue[HttpPushMessage] = asyncio.Queue()


async def push_handler(message: HttpPushMessage):
    _logger.info(
        "Putting HTTP Push request into the queue:\n%s", pprint.pformat(message.dict())
    )

    await _queue.put(message)


async def main():
    # Start the Rabbit broker and set the handler for the HTTP push messages
    # received on the Consumer Backend from the Provider.
    await start_messaging_app(http_push_handler=push_handler)

    # The orchestrator contains the logic to interact with the EDC HTTP APIs.
    # https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api/0.1.0-SNAPSHOT
    config = ConsumerProviderPairConfig.from_env()
    orchestrator = RequestOrchestrator(config=config)
    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    # Initiate the transfer processfor the asset.
    transfer_details = await orchestrator.prepare_to_transfer_asset(
        asset_query=_ASSET_CONSUMPTION
    )

    transfer_process = await orchestrator.create_provider_push_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
        sink_base_url=_SINK_BASE_URL,
        sink_path=_SINK_PATH,
        sink_method=_SINK_METHOD,
    )

    transfer_process_id = transfer_process["@id"]

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )

    # Wait for the message published by the Consumer Backend to the Rabbit broker.
    # The message contains the response from the Mock HTTP API without any modification.
    # That is, the message has been 'pushed' from the Provider to the Consumer Backend.
    http_push_msg = await _queue.get()

    _logger.info(
        "Received response from Mock HTTP API:\n%s", pprint.pformat(http_push_msg.body)
    )


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv("LOG_LEVEL", "DEBUG"))
    asyncio.run(main())
