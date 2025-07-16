"""
EDC Parallel HTTP Pull Data Transfer Example

This example demonstrates how to:
1. Execute multiple concurrent data transfer requests to the same EDC provider
2. Handle parallel responses using message filtering by transfer process ID
3. Process results from multiple requests simultaneously using asyncio.gather()

This approach is useful when you need to make multiple data requests efficiently,
such as requesting data for different time periods or locations in parallel.
The key advantage is significantly reduced total execution time compared to
sequential requests.
"""

import asyncio
import logging
import pprint
import uuid
from typing import Optional
from urllib.parse import urlparse

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController
from edcpy.messaging import MessagingClient

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    """Configuration for the parallel HTTP pull example."""

    # EDC provider details
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")

    # Asset queries for parallel requests (both POST)
    asset_query_post: str = environ.var(default="POST-consumption-prediction")

    # Queue configuration
    consumer_id: Optional[str] = environ.var(default=None)
    queue_timeout_seconds: int = environ.var(default=60, converter=int)

    # Logging
    log_level: str = environ.var(default="INFO")

    # Parallelism
    num_requests: int = environ.var(default=5, converter=int)


async def execute_parallel_request(
    asset_query: str,
    request_name: str,
    config: AppConfig,
    controller: ConnectorController,
    consumer,
    post_body: dict = None,
):
    """Execute a single data transfer request as part of a parallel operation.

    This function encapsulates the complete EDC data transfer workflow:
    1. Contract negotiation with the provider
    2. Transfer process initiation
    3. Credential receipt via RabbitMQ
    4. Direct HTTP request to provider's data endpoint
    """

    _logger.info("Starting %s request for asset: %s", request_name, asset_query)

    # Step 1: Negotiate contract with provider
    # This establishes the terms and conditions for data access
    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=asset_query,
    )

    # Step 2: Start transfer process for pull mechanism
    # This initiates the data transfer and returns a unique process ID
    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    _logger.info("%s transfer started: %s", request_name, transfer_process_id)

    # Step 3: Wait for pull credentials filtered by transfer process ID
    # This ensures we get the right message even with multiple parallel requests
    async with consumer.wait_for_message(
        expected_id=transfer_process_id,
        timeout=config.queue_timeout_seconds,
    ) as http_pull_message:
        async with httpx.AsyncClient() as client:
            # Prepare HTTP request with credentials received from EDC
            request_kwargs = http_pull_message.request_args

            # Add POST body for requests that require it
            if post_body:
                request_kwargs["json"] = post_body

            _logger.info(
                "%s executing request with credentials:\n%s",
                request_name,
                pprint.pformat(request_kwargs),
            )

            # Execute the authenticated HTTP request to get actual data
            response = await client.request(**request_kwargs)
            data = response.json()

            _logger.info("%s completed:\n%s", request_name, pprint.pformat(data))

            return data


async def main(config: AppConfig):
    """Main function demonstrating parallel HTTP pull data transfers.

    This example shows how to handle multiple parallel requests to the same EDC connector.
    It is useful when acting as a gateway for several end users who may request data concurrently and independently.
    """

    # Create messaging client for RabbitMQ communication
    consumer_id = config.consumer_id or f"consumer-{uuid.uuid4().hex[:8]}"
    client = MessagingClient(consumer_id)

    # Extract provider host from counter party protocol URL
    provider_host = urlparse(config.counter_party_protocol_url).hostname

    # Start pull consumer to receive credentials from EDC
    # Optionally set provider host to avoid routing unnecessary messages to queues
    async with client.pull_consumer(
        timeout=config.queue_timeout_seconds, provider_host=provider_host
    ) as consumer:
        _logger.info("Messaging consumer started, ready to receive credentials")

        # Initialize EDC controller for managing transfers
        controller = ConnectorController()
        _logger.debug("EDC Controller configuration:\n%s", controller.config)

        # Configure parallel requests
        locations = ["Asturias", "Bizkaia", "Pontevedra", "Girona", "Cantabria"]

        # Generate unique POST bodies for each request
        # This simulates requesting data for different time periods and locations
        post_bodies = []

        for i in range(config.num_requests):
            post_bodies.append(
                {
                    "date_from": f"2023-06-{10 + i:02d}T14:30:00",
                    "date_to": f"2023-06-{10 + i:02d}T18:00:00",
                    "location": locations[i % len(locations)],
                }
            )

        _logger.info(
            "Starting parallel execution of %d POST requests", config.num_requests
        )

        # Create async tasks for parallel execution
        # Each task will independently negotiate, transfer, and fetch data
        tasks = []

        for i, post_body in enumerate(post_bodies):
            task = execute_parallel_request(
                asset_query=config.asset_query_post,
                request_name=f"POST{i+1}",
                config=config,
                controller=controller,
                consumer=consumer,
                post_body=post_body,
            )

            tasks.append(task)

        # Execute all requests concurrently and wait for all to complete
        results = await asyncio.gather(*tasks)

        # Verify that responses match the requested parameters
        for i, result in enumerate(results):
            assert result["location"] == post_bodies[i]["location"]

        _logger.info("All parallel requests completed successfully")
        return results


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
