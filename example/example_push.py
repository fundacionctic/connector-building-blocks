"""
EDC HTTP Push Data Transfer Example

This example demonstrates how to:
1. Negotiate data access contracts with an EDC provider
2. Configure the provider to push data to your HTTP endpoint
3. Receive and process the pushed data via RabbitMQ messaging

In push transfers, the provider sends data to a consumer-specified endpoint
when the data becomes available. This is suitable for real-time data delivery
where the provider controls when to send the data. Consumer-specific queues
are used for efficient message routing without complex filtering.
"""

import asyncio
import logging
import pprint

import coloredlogs
import environ

from edcpy.edc_api import ConnectorController
from edcpy.message_handler import MessageConsumer
from edcpy.messaging import MessagingClient

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    """Configuration for the HTTP push example."""

    # EDC provider details
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")
    asset_query: str = environ.var(default="GET-consumption")

    # Consumer HTTP endpoint where provider will push data
    consumer_backend_base_url: str = environ.var(default="http://consumer.local:8000")
    consumer_backend_push_path: str = environ.var(default="/push")
    consumer_backend_push_method: str = environ.var(default="POST")

    # Queue configuration
    consumer_id: str = environ.var(default="example-push-consumer")
    routing_path: str = environ.var(default="specific/routing/key")
    queue_timeout_seconds: int = environ.var(default=20, converter=int)

    # Logging
    log_level: str = environ.var(default="DEBUG")


async def run_push_transfer(
    config: AppConfig,
    controller: ConnectorController,
    consumer: MessageConsumer,
):
    """Execute HTTP push transfer and process received data.

    This function demonstrates the complete push workflow:
    1. Negotiate contract with provider to establish data access rights
    2. Configure provider to push data to our HTTP endpoint
    3. Wait for and process the pushed data from RabbitMQ

    Returns:
        dict: The pushed data received from the provider
    """

    # Step 1: Negotiate contract with provider
    # This establishes the legal and technical framework for data access
    _logger.info("Negotiating contract for asset: %s", config.asset_query)

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=config.asset_query,
    )

    # Step 2: Configure provider to push data to our HTTP endpoint
    # The routing path ensures messages are delivered to our specific queue
    # The provider will make HTTP requests to this endpoint when data is ready
    sink_path = f"{config.consumer_backend_push_path}/{config.routing_path}"

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details,
        is_provider_push=True,
        sink_base_url=config.consumer_backend_base_url,
        sink_path=sink_path,
        sink_method=config.consumer_backend_push_method,
    )

    _logger.info("Transfer process started: %s", transfer_process_id)

    # Step 3: Wait for and process the pushed data
    # No filtering needed - consumer queue only receives our messages
    async with consumer.wait_for_message(
        timeout=config.queue_timeout_seconds
    ) as http_push_message:
        _logger.info(
            "Received pushed data from provider:\n%s",
            pprint.pformat(http_push_message.body),
        )

        # Process the data here as needed
        # In a real application, you would parse, validate, and store the data
        return http_push_message.body


async def main(config: AppConfig):
    """Main function demonstrating HTTP push data transfer."""

    # Create messaging client for RabbitMQ communication
    client = MessagingClient(config.consumer_id)

    # Start push consumer with routing path and timeout
    async with client.push_consumer(
        routing_path=config.routing_path, timeout=config.queue_timeout_seconds
    ) as consumer:
        _logger.info("Messaging app started, ready to receive data")

        # Initialize EDC controller
        controller = ConnectorController()
        _logger.debug("EDC Controller configuration:\n%s", controller.config)

        # Execute the push transfer
        result = await run_push_transfer(
            config=config,
            controller=controller,
            consumer=consumer,
        )

        _logger.info("Push transfer completed successfully")
        return result


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
