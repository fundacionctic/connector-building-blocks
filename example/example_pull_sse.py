"""
EDC HTTP Pull Data Transfer Example using SSE API

This example demonstrates how to:
1. Negotiate data access contracts with an EDC provider
2. Receive pull credentials via SSE (Server-Sent Events) API
3. Use the credentials to make authenticated HTTP GET requests to the provider

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
    """Configuration for the SSE HTTP pull example."""

    # EDC provider details
    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )

    counter_party_connector_id: str = environ.var(default="example-provider")

    # Asset query for GET method
    asset_query_get: str = environ.var(default="GET-consumption")

    # Consumer Backend SSE API configuration
    consumer_backend_url: str = environ.var(default="http://localhost:28000")
    sse_timeout_seconds: int = environ.var(default=60, converter=int)

    # The SSE Consumer Backend endpoints use the same API key as the connector by default
    api_auth_key: str = environ.var(name="EDC_CONNECTOR_API_KEY")

    # Logging
    log_level: str = environ.var(default="DEBUG")


class SSEPullCredentialsReceiver:
    """Helper class to receive pull credentials via SSE API."""

    def __init__(self, config: AppConfig):
        self.config = config

        self.headers = {
            "Authorization": f"Bearer {config.api_auth_key}",
            "Accept": "text/event-stream",
        }

    async def wait_for_credentials(self, transfer_process_id: str) -> Dict[str, Any]:
        """Wait for pull credentials via SSE for a specific transfer process."""

        url = f"{self.config.consumer_backend_url}/pull/stream/{transfer_process_id}"
        params = {"timeout": self.config.sse_timeout_seconds}

        _logger.info(f"Connecting to SSE endpoint: {url}")
        _logger.debug(f"SSE parameters: {params}")

        timeout = httpx.Timeout(
            connect=5.0,
            read=self.config.sse_timeout_seconds + 10,
            write=5.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                raise Exception(
                    f"SSE connection failed: {response.status_code} {response.text}"
                )

            _logger.info("SSE connection established, waiting for pull credentials")

            for line in response.text.split("\n"):
                line = line.strip()

                if not line.startswith("data: "):
                    continue

                data_json = line[6:]  # Remove 'data: ' prefix

                try:
                    message = json.loads(data_json)
                    _logger.debug(f"Received SSE message: {message}")

                    if message.get("type") == "pull_message":
                        _logger.info("Pull credentials received via SSE")
                        return message
                    elif message.get("type") == "error":
                        raise Exception(
                            f"SSE error: {message.get('message', 'Unknown error')}"
                        )
                except json.JSONDecodeError:
                    _logger.warning(f"Invalid JSON in SSE message: {data_json}")
                    continue

            raise Exception("SSE stream ended without receiving pull credentials")


async def execute_get_request(
    config: AppConfig,
    controller: ConnectorController,
    sse_receiver: SSEPullCredentialsReceiver,
):
    """Execute HTTP GET request using EDC pull mechanism with SSE API.

    This function demonstrates the complete pull workflow for GET requests:
    1. Negotiate contract with provider to establish data access rights
    2. Start pull transfer process to request credentials
    3. Receive pull credentials via SSE API
    4. Use credentials to make authenticated HTTP GET request to provider
    """

    # Step 1: Negotiate contract for GET asset
    _logger.info("Negotiating contract for GET asset: %s", config.asset_query_get)

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=config.counter_party_protocol_url,
        counter_party_connector_id=config.counter_party_connector_id,
        asset_query=config.asset_query_get,
    )

    # Step 2: Start pull transfer process
    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    _logger.info("Pull transfer started: %s", transfer_process_id)

    # Step 3: Receive pull credentials via SSE and execute GET request
    pull_message = await sse_receiver.wait_for_credentials(transfer_process_id)

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Executing GET request with SSE credentials:\n%s",
            pprint.pformat(pull_message.get("request_args", {})),
        )

        # Make authenticated request to provider's data endpoint
        response = await client.request(**pull_message["request_args"])
        data = response.json()

        _logger.info("GET response received:\n%s", pprint.pformat(data))
        return data


async def main(config: AppConfig):
    """Main function demonstrating HTTP pull data transfer using SSE API.

    This example shows how to perform a data request using the
    SSE API instead of native Python messaging, making it suitable for
    browser-based applications or simplified integration scenarios.
    """

    # Create SSE receiver for pull credentials
    sse_receiver = SSEPullCredentialsReceiver(config)

    # Initialize EDC controller for managing transfers
    controller = ConnectorController()
    _logger.debug("EDC Controller configuration:\n%s", controller.config)

    # Execute GET request
    _logger.info("Starting GET request via SSE API")

    result = await execute_get_request(
        config=config,
        controller=controller,
        sse_receiver=sse_receiver,
    )

    _logger.info("SSE pull transfer completed successfully")
    return result


if __name__ == "__main__":
    config: AppConfig = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
