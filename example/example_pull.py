import asyncio
import logging
import pprint

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController
from edcpy.message_handler import MessageHandler, create_handler_function
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


async def request_get(
    cnf: AppConfig,
    controller: ConnectorController,
    message_handler: MessageHandler[HttpPullMessage],
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

    # Use the message handler's context manager for automatic ack/nack handling
    async with message_handler.process_message(
        timeout_seconds=cnf.queue_timeout_seconds, expected_id=transfer_process_id
    ) as http_pull_message:
        async with httpx.AsyncClient() as client:
            _logger.info(
                "Sending HTTP GET request with arguments:\n%s",
                pprint.pformat(http_pull_message.request_args),
            )

            resp = await client.request(**http_pull_message.request_args)
            _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def request_post(
    cnf: AppConfig,
    controller: ConnectorController,
    message_handler: MessageHandler[HttpPullMessage],
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

    # Use the message handler's context manager for automatic ack/nack handling
    async with message_handler.process_message(
        timeout_seconds=cnf.queue_timeout_seconds, expected_id=transfer_process_id
    ) as http_pull_message:
        async with httpx.AsyncClient() as client:
            # The body of the POST request is passed as a JSON object.
            # Previous knowledge of the request body schema is required.
            post_body = {
                "date_from": "2023-06-15T14:30:00",
                "date_to": "2023-06-15T18:00:00",
                "location": "Asturias",
            }

            request_kwargs = {**http_pull_message.request_args, "json": post_body}

            _logger.info(
                "Sending HTTP POST request with arguments:\n%s",
                pprint.pformat(request_kwargs),
            )

            resp = await client.request(**request_kwargs)

            _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def main(cnf: AppConfig):
    # Configuration for acknowledgment mode
    auto_acknowledge = False

    # Create a message handler for HTTP Pull messages
    # Set max_nack_attempts to 3 to prevent infinite loops
    message_handler = MessageHandler(
        HttpPullMessage, auto_acknowledge=auto_acknowledge, max_nack_attempts=3
    )

    # Create the handler function for the messaging system
    pull_handler_func = create_handler_function(message_handler)

    # Start the Rabbit broker and set the handler for the HTTP pull messages
    # (EndpointDataReference) received on the Consumer Backend from the Provider.
    async with with_messaging_app(
        http_pull_handler=pull_handler_func, auto_acknowledge=auto_acknowledge
    ):
        controller = ConnectorController()
        _logger.debug("Configuration:\n%s", controller.config)

        # Note that the "Mock Backend" HTTP API is a regular HTTP API
        # that does not implement any data space-specific logic.
        await request_get(
            cnf=cnf, controller=controller, message_handler=message_handler
        )

        await request_post(
            cnf=cnf, controller=controller, message_handler=message_handler
        )


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(cnf=config))
