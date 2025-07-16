"""
EDC HTTP Pull Data Transfer Example using SSE API

This example demonstrates how to:
1. Start listening for pull credentials from a provider via SSE
2. Negotiate data access contracts with an EDC provider
3. Receive pull credentials and make authenticated HTTP requests

This uses the provider host-based SSE endpoint to avoid timing issues.
"""

import asyncio
import json
import logging
import pprint
from typing import Dict, Optional
from urllib.parse import urlparse

import coloredlogs
import environ
import httpx

from edcpy.edc_api import ConnectorController

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class AppConfig:
    """Configuration for the SSE HTTP pull example."""

    counter_party_protocol_url: str = environ.var(
        default="http://provider.local:9194/protocol"
    )
    counter_party_connector_id: str = environ.var(default="example-provider")
    asset_query_get: str = environ.var(default="GET-consumption")
    consumer_backend_url: str = environ.var(default="http://localhost:28000")
    api_auth_key: str = environ.var(name="EDC_CONNECTOR_API_KEY")
    log_level: str = environ.var(default="DEBUG")


class SSEPullCredentialsReceiver:
    """Receives pull credentials from the provider's SSE endpoint,
    allowing you to start listening before the Transfer Process ID is known.
    This ensures you do not miss the access token message."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_auth_key}",
            "Accept": "text/event-stream",
        }

        # One future per transfer ID. The future is set exactly once
        # with the pull-message dict.
        self._futures: Dict[str, asyncio.Future] = {}

        # Background listener task and a flag that becomes true once the
        # SSE connection is confirmed (HTTP 200).
        self._listener_task: Optional[asyncio.Task] = None
        self._connected_event: asyncio.Event = asyncio.Event()

    async def start_listening(self, protocol_url: str):
        """Start the background SSE listener.

        The coroutine returns once the HTTP stream is ready, so callers
        can safely trigger contract negotiation without the risk of
        missing the first credential message.
        """

        if self._listener_task and not self._listener_task.done():
            _logger.warning("SSE listener already running")
            return

        provider_host = urlparse(protocol_url).hostname
        url = f"{self.config.consumer_backend_url}/pull/stream/provider/{provider_host}"

        _logger.info(f"Connecting to SSE stream for provider: {provider_host}")
        self._connected_event.clear()
        self._listener_task = asyncio.create_task(self._listen_sse_stream(url))

        # Wait until the HTTP 200 response has been received (or fail fast)
        await asyncio.wait_for(self._connected_event.wait(), timeout=5)

    async def _listen_sse_stream(self, url: str):
        """Internal task: consume the SSE stream and resolve futures."""

        timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", url, headers=self.headers) as response:
                    if response.status_code != 200:
                        raise Exception(
                            f"SSE connection failed: {response.status_code}"
                        )

                    _logger.info("SSE stream connected")
                    self._connected_event.set()

                    async for line in response.aiter_lines():
                        if not line.strip().startswith("data: "):
                            continue

                        try:
                            message = json.loads(line.strip()[6:])  # remove 'data: '
                        except json.JSONDecodeError:
                            _logger.warning(f"Invalid JSON in SSE message: {line}")
                            continue

                        if message.get("type") != "pull_message":
                            continue

                        transfer_id = message.get("transfer_process_id")

                        if not transfer_id:
                            continue

                        # Resolve or store the future for this transfer ID
                        future = self._futures.get(transfer_id)

                        if future is None:
                            future = asyncio.get_event_loop().create_future()
                            self._futures[transfer_id] = future

                        if not future.done():
                            _logger.info(
                                f"Received credentials for transfer: {transfer_id}"
                            )
                            future.set_result(message)

        except Exception as e:
            # Ensure listeners are not left waiting forever
            self._connected_event.set()
            _logger.error(f"SSE listener error: {e}")

    async def get_credentials(self, transfer_id: str, timeout: float = 60.0) -> dict:
        """Await the credentials for transfer_id (with timeout)."""

        future = self._futures.get(transfer_id)

        if future is None:
            future = asyncio.get_event_loop().create_future()
            self._futures[transfer_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise Exception(
                f"Timeout waiting for credentials for transfer: {transfer_id}"
            ) from exc

    async def stop_listening(self):
        """Cancel the listener task and clear pending futures."""

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()

            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._futures.clear()
        self._connected_event.clear()


async def main():
    """Main function demonstrating provider-based SSE pull data transfer."""

    config = AppConfig.from_environ()
    sse_receiver = SSEPullCredentialsReceiver(config)
    controller = ConnectorController()

    try:
        _logger.info(f"Starting data transfer for asset: {config.asset_query_get}")

        # Step 1: Start listening for SSE events immediately
        await sse_receiver.start_listening(config.counter_party_protocol_url)

        # Step 2: Negotiate contract
        transfer_details = await controller.run_negotiation_flow(
            counter_party_protocol_url=config.counter_party_protocol_url,
            counter_party_connector_id=config.counter_party_connector_id,
            asset_query=config.asset_query_get,
        )

        # Step 3: Start transfer
        transfer_id = await controller.run_transfer_flow(
            transfer_details=transfer_details, is_provider_push=False
        )

        _logger.info(f"Transfer process started: {transfer_id}")

        # Step 4: Get credentials (either from buffer or wait for them)
        pull_message = await sse_receiver.get_credentials(transfer_id)

        # Step 5: Execute the authenticated request
        async with httpx.AsyncClient() as client:
            _logger.info("Executing authenticated GET request")
            response = await client.request(**pull_message["request_args"])
            data = response.json()
            _logger.info("GET response received:\n%s", pprint.pformat(data))
            return data

    finally:
        # Clean up the SSE listener
        await sse_receiver.stop_listening()


if __name__ == "__main__":
    config = AppConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main())
