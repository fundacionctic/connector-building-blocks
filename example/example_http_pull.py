"""
An example of using the Transfer Data Plane extension
(https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane)
to call an arbitrary HTTP API that is exposed by the Provider.
More specifically, this example demonstrates the Consumer Pull use case.
"""

import asyncio
import logging
import pprint

import coloredlogs
import httpx

from edcpy.config import ConsumerProviderPairConfig
from edcpy.messaging import HttpPullMessage, start_messaging_app
from edcpy.orchestrator import RequestOrchestrator

# These asset names are known in advance and are used to query the provider.
# However, they could be selected dynamically by browsing the catalogue.
# In any case, some knowledge of the schema of the request body is required.
_ASSET_ASYNCAPI_JSON = "asyncapi-json"
_ASSET_CONSUMPTION_PREDICTION = "consumption-prediction"

_logger = logging.getLogger(__name__)
_queue: asyncio.Queue[HttpPullMessage] = asyncio.Queue()


async def pull_handler(message: HttpPullMessage):
    """This handler is called when a message is received
    from the HTTP Pull queue in the Rabbit broker."""

    _logger.info(
        "Putting HTTP Pull request into the queue:\n%s", pprint.pformat(message.dict())
    )

    await _queue.put(message)


async def transfer_asset(orchestrator: RequestOrchestrator, asset_query: str):
    """A helper function to handle the transfer process of an asset."""

    transfer_details = await orchestrator.prepare_to_transfer_asset(
        asset_query=asset_query
    )

    transfer_process = await orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )


async def main():
    # Start the Rabbit broker and set the handler for the HTTP pull messages
    # (EndpointDataReference) received from the provider's side.
    await start_messaging_app(http_pull_handler=pull_handler)

    # The orchestrator contains the logic to interact with the EDC HTTP APIs.
    config = ConsumerProviderPairConfig.from_env()
    orchestrator = RequestOrchestrator(config=config)
    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    # First, we request a GET endpoint from the mock HTTP API that is exposed by the provider.
    # Please note that in this case the mock HTTP API is a regular
    # HTTP API that is not aware of the particularities of our data space.
    await transfer_asset(asset_query=_ASSET_ASYNCAPI_JSON, orchestrator=orchestrator)

    http_pull_msg_get = await _queue.get()

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP request with arguments:\n%s",
            pprint.pformat(http_pull_msg_get.request_args),
        )

        resp_get = await client.request(**http_pull_msg_get.request_args)
        _logger.info("Response:\n%s", pprint.pformat(resp_get.json()))

    # Now we demonstrate how to call a POST endpoint passing a JSON body,
    # which is arguably a more complex use case.
    await transfer_asset(
        asset_query=_ASSET_CONSUMPTION_PREDICTION, orchestrator=orchestrator
    )

    http_pull_msg_post = await _queue.get()

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP request with arguments:\n%s",
            pprint.pformat(http_pull_msg_post.request_args),
        )

        # The body of the POST request is passed as a JSON object.
        # Some knowledge of the request body schema is required.
        post_body = {
            "date_from": "2023-06-15T14:30:00",
            "date_to": "2023-06-15T18:00:00",
            "location": "Asturias",
        }

        resp_post = await client.request(
            **http_pull_msg_post.request_args, json=post_body
        )

        _logger.info("Response:\n%s", pprint.pformat(resp_post.json()))


if __name__ == "__main__":
    coloredlogs.install(level=logging.DEBUG)
    asyncio.run(main())
