"""
EDC HTTP Push Data Transfer Example using SSE API

This example demonstrates how to:
1. Negotiate data access contracts with an EDC provider
2. Configure the provider to push data to your HTTP endpoint
3. Receive and process the pushed data via SSE (Server-Sent Events) API

This is an alternative to the native Python messaging API that uses HTTP
Server-Sent Events for browser compatibility.
"""

import asyncio
import json
import logging
import pprint
from typing import Any, Dict

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    """Configuration for the SSE HTTP push example."""

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

    # Consumer Backend SSE API configuration
    consumer_backend_url: str = environ.var(default="http://localhost:28000")
    routing_path: str = environ.var(default="specific/routing/key")

    # The SSE Consumer Backend endpoints use the same API key as the connector by default
    api_auth_key: str = environ.var(name="EDC_CONNECTOR_API_KEY")

    # Logging
    log_level: str = environ.var(default="DEBUG")


class SSEPushMessageReceiver:
    """Helper class to receive push messages via SSE API."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_auth_key}",
            "Accept": "text/event-stream",
        }

    async def wait_for_push_message(self, routing_path: str) -> Dict[str, Any]:
        """Wait for push message via SSE for a specific routing path."""

        url = f"{self.config.consumer_backend_url}/push/stream/{routing_path}"

        _logger.info(f"Connecting to SSE endpoint: {url}")

        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code != 200:
                raise Exception(
                    f"SSE connection failed: {response.status_code} {response.text}"
                )

            _logger.info("SSE connection established, waiting for push message")

            for line in response.text.split("\n"):
                line = line.strip()

                if not line.startswith("data: "):
                    continue

                data_json = line[6:]  # Remove 'data: ' prefix

                try:
                    message = json.loads(data_json)
                    _logger.debug(f"Received SSE message: {message}")

                    if message.get("type") == "push_message":
                        _logger.info("Push message received via SSE")
                        return message
                    elif message.get("type") == "error":
                        raise Exception(
                            f"SSE error: {message.get('message', 'Unknown error')}"
                        )
                except json.JSONDecodeError:
                    _logger.warning(f"Invalid JSON in SSE message: {data_json}")
                    continue

            raise Exception("SSE stream ended without receiving push message")


async def run_push_transfer(
    config: AppConfig,
    controller: ConnectorController,
    sse_receiver: SSEPushMessageReceiver,
):
    """Execute HTTP push transfer and process received data using SSE API.

    This function demonstrates the complete push workflow:
    1. Negotiate contract with provider to establish data access rights
    2. Configure provider to push data to our HTTP endpoint
    3. Wait for and process the pushed data via SSE API

    Returns:
        dict: The pushed data received from the provider
    """

    # Step 1: Negotiate contract with provider
    _logger.info("Negotiating contract for asset: %s", config.asset_query)

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=config.asset_query,
    )

    # Step 2: Configure provider to push data to our HTTP endpoint
    # The routing path ensures messages are delivered to our specific queue
    sink_path = f"{config.consumer_backend_push_path}/{config.routing_path}"

    # Step 2 & 3: Run transfer and wait for push message concurrently
    transfer_task = controller.run_transfer_flow(
        transfer_details=transfer_details,
        is_provider_push=True,
        sink_base_url=config.consumer_backend_base_url,
        sink_path=sink_path,
        sink_method=config.consumer_backend_push_method,
    )

    sse_task = sse_receiver.wait_for_push_message(config.routing_path)

    # Wait for both tasks concurrently to avoid missing the push message.
    transfer_process_id, push_message = await asyncio.gather(transfer_task, sse_task)

    _logger.info("Transfer process ID: %s", transfer_process_id)

    _logger.info(
        "Received pushed data from provider via SSE:\n%s",
        pprint.pformat(push_message.get("body", {})),
    )

    # Process the data here as needed
    # In a real application, you would parse, validate, and store the data
    return push_message.get("body", {})


async def main(config: AppConfig):
    """Main function demonstrating HTTP push data transfer using SSE API.

    This example shows how to receive pushed data using the
    SSE API instead of native Python messaging, making it suitable for
    browser-based applications or simplified integration scenarios.
    """

    # Create SSE receiver for push messages
    sse_receiver = SSEPushMessageReceiver(config)
    _logger.info("SSE receiver ready to receive push messages")

    # Initialize EDC controller for managing transfers
    controller = ConnectorController()
    _logger.debug("EDC Controller configuration:\n%s", controller.config)

    # Execute push transfer
    _logger.info("Starting push transfer via SSE API")

    result = await run_push_transfer(
        config=config,
        controller=controller,
        sse_receiver=sse_receiver,
    )

    _logger.info("SSE push transfer completed successfully")
    return result


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
