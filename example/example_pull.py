import asyncio
import logging
import os
import pprint

import coloredlogs
import httpx

from edcpy.edc_api import ConnectorController
from edcpy.messaging import HttpPullMessage, with_messaging_app

_ENV_LOG_LEVEL = "LOG_LEVEL"
_ENV_COUNTER_PARTY_PROTOCOL_URL = "COUNTER_PARTY_PROTOCOL_URL"
_ENV_COUNTER_PARTY_CONNECTOR_ID = "COUNTER_PARTY_CONNECTOR_ID"
_ENV_ASSET_QUERY_GET = "ASSET_QUERY_GET"
_QUEUE_GET_TIMEOUT_SECS = 20

_logger = logging.getLogger(__name__)


async def pull_handler(message: dict, queue: asyncio.Queue):
    """Put an HTTP Pull message received from the Rabbit broker into a queue."""

    # Using type hints for the message argument seems to break in Python 3.8.
    message = HttpPullMessage(**message)

    _logger.info(
        "Putting HTTP Pull request into the queue:\n%s", pprint.pformat(message.dict())
    )

    # Using a queue is not strictly necessary.
    # We just need an asyncio-compatible way to pass
    # the messages from the broker to the main function.
    await queue.put(message)


async def request_get(controller: ConnectorController, queue: asyncio.Queue):
    """Demonstration of a GET request to the Mock HTTP API."""

    counter_party_protocol_url: str = os.getenv(
        _ENV_COUNTER_PARTY_PROTOCOL_URL, "http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = os.getenv(
        _ENV_COUNTER_PARTY_CONNECTOR_ID, "example-provider"
    )

    asset_query: str = os.getenv(_ENV_ASSET_QUERY_GET, "GET-consumption")

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=counter_party_protocol_url,
        counter_party_connector_id=counter_party_connector_id,
        asset_query=asset_query,
    )

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    http_pull_msg = await asyncio.wait_for(queue.get(), timeout=_QUEUE_GET_TIMEOUT_SECS)

    if http_pull_msg.id != transfer_process_id:
        raise RuntimeError(
            "The ID of the Transfer Process does not match the ID of the HTTP Pull message"
        )

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP GET request with arguments:\n%s",
            pprint.pformat(http_pull_msg.request_args),
        )

        resp = await client.request(**http_pull_msg.request_args)
        _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def main():
    queue: asyncio.Queue[HttpPullMessage] = asyncio.Queue()

    async def pull_handler_partial(message: dict):
        await pull_handler(message=message, queue=queue)

    # Start the Rabbit broker and set the handler for the HTTP pull messages
    # (EndpointDataReference) received on the Consumer Backend from the Provider.
    async with with_messaging_app(http_pull_handler=pull_handler_partial):
        controller = ConnectorController()
        _logger.debug("Configuration:\n%s", controller.config)

        # Note that the "Mock Backend" HTTP API is a regular HTTP API
        # that does not implement any data space-specific logic.
        await request_get(controller=controller, queue=queue)


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv(_ENV_LOG_LEVEL, "DEBUG"))
    asyncio.run(main())
