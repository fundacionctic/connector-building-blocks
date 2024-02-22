import asyncio
import logging
import pprint

import coloredlogs
import environ

from edcpy.edc_api import ConnectorController
from edcpy.messaging import HttpPullMessage, HttpPushMessage, with_messaging_app

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


async def push_handler(message: dict, queue: asyncio.Queue):
    # Using type hints for the message argument seems to break in Python 3.8.
    message = HttpPushMessage(**message)

    _logger.info(
        "Putting HTTP Push request into the queue:\n%s", pprint.pformat(message.dict())
    )

    await queue.put(message)


async def run_request(
    cnf: AppConfig, controller: ConnectorController, queue: asyncio.Queue
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

    http_push_msg = await asyncio.wait_for(
        queue.get(), timeout=cnf.queue_timeout_seconds
    )

    _logger.info(
        "Received response from Mock Backend HTTP API:\n%s",
        pprint.pformat(http_push_msg.body),
    )


async def main(cnf: AppConfig):
    queue: asyncio.Queue[HttpPullMessage] = asyncio.Queue()

    async def push_handler_partial(message: dict):
        await push_handler(message=message, queue=queue)

    # Start the Rabbit broker and set the handler for the HTTP pull messages
    # (EndpointDataReference) received on the Consumer Backend from the Provider.
    async with with_messaging_app(http_push_handler=push_handler_partial):
        controller = ConnectorController()
        _logger.debug("Configuration:\n%s", controller.config)
        await run_request(cnf=cnf, controller=controller, queue=queue)


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(cnf=config))
