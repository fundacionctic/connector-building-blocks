import asyncio
import logging
import pprint

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController
from edcpy.messaging import HttpPullMessage, with_messaging_app

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")
    asset_query_get: str = environ.var(default="GET-consumption")
    asset_query_post: str = environ.var(default="POST-consumption-prediction")
    queue_timeout_seconds: int = environ.var(default=20, converter=int)
    log_level: str = environ.var(default="DEBUG")


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


async def request_get(
    cnf: AppConfig, controller: ConnectorController, queue: asyncio.Queue
):
    """Demonstration of a GET request to the Mock HTTP API."""

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=cnf.counter_party_protocol_url,
        counter_party_connector_id=cnf.counter_party_connector_id,
        asset_query=cnf.asset_query_get,
    )

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    http_pull_msg = await asyncio.wait_for(
        queue.get(), timeout=cnf.queue_timeout_seconds
    )

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


async def request_post(
    cnf: AppConfig, controller: ConnectorController, queue: asyncio.Queue
):
    """Demonstration of how to call a POST endpoint of the Mock HTTP API passing a JSON body."""

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=cnf.counter_party_protocol_url,
        counter_party_connector_id=cnf.counter_party_connector_id,
        asset_query=cnf.asset_query_post,
    )

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    http_pull_msg = await asyncio.wait_for(
        queue.get(), timeout=cnf.queue_timeout_seconds
    )

    if http_pull_msg.id != transfer_process_id:
        raise RuntimeError(
            "The ID of the Transfer Process does not match the ID of the HTTP Pull message"
        )

    async with httpx.AsyncClient() as client:
        # The body of the POST request is passed as a JSON object.
        # Previous knowledge of the request body schema is required.
        post_body = {
            "date_from": "2023-06-15T14:30:00",
            "date_to": "2023-06-15T18:00:00",
            "location": "Asturias",
        }

        request_kwargs = {**http_pull_msg.request_args, "json": post_body}

        _logger.info(
            "Sending HTTP POST request with arguments:\n%s",
            pprint.pformat(request_kwargs),
        )

        resp = await client.request(**request_kwargs)

        _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def main(cnf: AppConfig):
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
        await request_get(cnf=cnf, controller=controller, queue=queue)
        await request_post(cnf=cnf, controller=controller, queue=queue)


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(cnf=config))
