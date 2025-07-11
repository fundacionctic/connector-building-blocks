import asyncio
import logging
import pprint

import coloredlogs
import environ

from edcpy.edc_api import ConnectorController
from edcpy.message_handler import MessageHandler, create_handler_function
from edcpy.messaging import HttpPushMessage, with_messaging_app

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")
    asset_query: str = environ.var(default="GET-consumption")
    queue_timeout_seconds: int = environ.var(default=20, converter=int)
    log_level: str = environ.var(default="DEBUG")
    consumer_backend_base_url: str = environ.var(default="http://consumer.local:8000")
    consumer_backend_push_path: str = environ.var(default="/push")
    consumer_backend_push_method: str = environ.var(default="POST")


async def run_request(
    cnf: AppConfig,
    controller: ConnectorController,
    message_handler: MessageHandler[HttpPushMessage],
):
    """Demonstration of how to call a POST endpoint of the Mock HTTP API passing a JSON body."""

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=cnf.counter_party_protocol_url,
        counter_party_connector_id=cnf.counter_party_connector_id,
        asset_query=cnf.asset_query,
    )

    # sink_base_url, sink_path and sink_method are the details of our local Consumer Backend.
    # Multiple path parameters can be added after the base path to be added to the routing key.
    # This enables us to "group" the push messages depending on the path called by the provider.
    sink_path = f"{cnf.consumer_backend_push_path}/specific/routing/key"

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details,
        is_provider_push=True,
        sink_base_url=cnf.consumer_backend_base_url,
        sink_path=sink_path,
        sink_method=cnf.consumer_backend_push_method,
    )

    _logger.info("Transfer process ID: %s", transfer_process_id)

    # Use the message handler's context manager for automatic ack/nack handling
    # Note: For push messages, we don't typically filter by transfer process ID
    # as the provider pushes data to us directly
    async with message_handler.process_message(
        timeout_seconds=cnf.queue_timeout_seconds
    ) as http_push_message:
        _logger.info(
            "Received response from Mock Backend HTTP API:\n%s",
            pprint.pformat(http_push_message.body),
        )


async def main(cnf: AppConfig):
    # Configuration for acknowledgment mode
    auto_acknowledge = False

    # Create a message handler for HTTP Push messages
    # Set max_nack_attempts to 3 to prevent infinite loops
    message_handler = MessageHandler(
        HttpPushMessage, auto_acknowledge=auto_acknowledge, max_nack_attempts=3
    )

    # Create the handler function for the messaging system
    push_handler_func = create_handler_function(message_handler)

    # Start the Rabbit broker and set the handler for the HTTP push messages
    # received on the Consumer Backend from the Provider.
    async with with_messaging_app(
        http_push_handler=push_handler_func, auto_acknowledge=auto_acknowledge
    ):
        controller = ConnectorController()
        _logger.debug("Configuration:\n%s", controller.config)

        await run_request(
            cnf=cnf, controller=controller, message_handler=message_handler
        )


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(cnf=config))
