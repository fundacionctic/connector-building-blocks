"""
EDC HTTP Pull Data Transfer Example

This example demonstrates how to:
1. Negotiate data access contracts with an EDC provider
2. Receive pull credentials via RabbitMQ messaging
3. Use the credentials to make authenticated HTTP requests to the provider
4. Handle both GET and POST requests using the pull mechanism

In pull transfers, the consumer receives credentials and makes direct HTTP
requests to the provider's data endpoints. This is suitable for on-demand
data access where the consumer controls when to fetch the data.
"""

import asyncio
import logging
import pprint

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController
from edcpy.messaging import MessagingClient

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    """Configuration for the HTTP pull example."""

    # EDC provider details
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")

    # Asset queries for different HTTP methods
    asset_query_get: str = environ.var(default="GET-consumption")
    asset_query_post: str = environ.var(default="POST-consumption-prediction")

    # Queue configuration
    consumer_id: str = environ.var(default="example-pull-consumer")
    queue_timeout_seconds: int = environ.var(default=60, converter=int)

    # Logging
    log_level: str = environ.var(default="DEBUG")


async def execute_get_request(
    config: AppConfig,
    controller: ConnectorController,
    consumer,
):
    """Execute HTTP GET request using EDC pull mechanism.

    This function demonstrates the complete pull workflow for GET requests:
    1. Negotiate contract with provider to establish data access rights
    2. Start pull transfer process to request credentials
    3. Receive pull credentials via RabbitMQ
    4. Use credentials to make authenticated HTTP GET request to provider

    Returns:
        dict: The JSON response data from the provider
    """

    # Step 1: Negotiate contract for GET asset
    # This establishes the legal and technical framework for data access
    _logger.info("Negotiating contract for GET asset: %s", config.asset_query_get)

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=config.asset_query_get,
    )

    # Step 2: Start pull transfer process
    # This requests the provider to prepare access credentials
    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    _logger.info("Pull transfer started: %s", transfer_process_id)

    # Step 3: Receive pull credentials and execute GET request
    # The credentials include URL, headers, and authentication tokens
    async with consumer.wait_for_message(
        timeout=config.queue_timeout_seconds
    ) as http_pull_message:
        async with httpx.AsyncClient() as client:
            _logger.info(
                "Executing GET request with credentials:\n%s",
                pprint.pformat(http_pull_message.request_args),
            )

            # Make authenticated request to provider's data endpoint
            response = await client.request(**http_pull_message.request_args)
            data = response.json()

            _logger.info("GET response received:\n%s", pprint.pformat(data))
            return data


async def execute_post_request(
    config: AppConfig,
    controller: ConnectorController,
    consumer,
):
    """Execute HTTP POST request using EDC pull mechanism.

    This function demonstrates the complete pull workflow for POST requests:
    1. Negotiate contract with provider to establish data access rights
    2. Start pull transfer process to request credentials
    3. Receive pull credentials via RabbitMQ
    4. Use credentials to make authenticated HTTP POST request with data
    """

    # Step 1: Negotiate contract for POST asset
    # This establishes the legal and technical framework for data access
    _logger.info("Negotiating contract for POST asset: %s", config.asset_query_post)

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=config.asset_query_post,
    )

    # Step 2: Start pull transfer process
    # This requests the provider to prepare access credentials
    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    _logger.info("Pull transfer started: %s", transfer_process_id)

    # Step 3: Receive pull credentials and execute POST request
    # The credentials include URL, headers, and authentication tokens
    async with consumer.wait_for_message(
        timeout=config.queue_timeout_seconds
    ) as http_pull_message:
        async with httpx.AsyncClient() as client:
            # Example POST body - adapt to your specific API requirements
            # This shows requesting consumption prediction data for a specific time/location
            post_body = {
                "date_from": "2023-06-15T14:30:00",
                "date_to": "2023-06-15T18:00:00",
                "location": "Asturias",
            }

            # Combine received credentials with POST body
            request_kwargs = {**http_pull_message.request_args, "json": post_body}

            _logger.info(
                "Executing POST request with credentials and body:\n%s",
                pprint.pformat(request_kwargs),
            )

            # Make authenticated POST request to provider's data endpoint
            response = await client.request(**request_kwargs)
            data = response.json()

            _logger.info("POST response received:\n%s", pprint.pformat(data))
            return data


async def main(config: AppConfig):
    """Main function demonstrating HTTP pull data transfer.

    This example shows how to perform sequential data requests using the
    pull mechanism, where the consumer receives credentials and makes
    direct HTTP requests to the provider's data endpoints.
    """

    # Create messaging client for RabbitMQ communication
    client = MessagingClient(config.consumer_id)

    # Start pull consumer to receive credentials from EDC
    async with client.pull_consumer(timeout=config.queue_timeout_seconds) as consumer:
        _logger.info("Messaging consumer started, ready to receive pull credentials")

        # Initialize EDC controller for managing transfers
        controller = ConnectorController()
        _logger.debug("EDC Controller configuration:\n%s", controller.config)

        # Execute GET request first
        # This demonstrates fetching data without sending any parameters
        get_result = await execute_get_request(
            config=config,
            controller=controller,
            consumer=consumer,
        )

        # Execute POST request second
        # This demonstrates sending parameters to retrieve specific data
        post_result = await execute_post_request(
            config=config,
            controller=controller,
            consumer=consumer,
        )

        _logger.info("All pull transfers completed successfully")
        return {"get_result": get_result, "post_result": post_result}


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
