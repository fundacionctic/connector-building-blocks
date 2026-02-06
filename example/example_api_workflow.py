"""
EDC Management API Workflow Example

This example demonstrates an end-to-end data exchange workflow where
assets, policies, and contract definitions are created directly via
the EDC Management API — without relying on the OpenAPI auto-generator.

This showcases how an external actor may integrate with the connector
if they prefer to use the EDC Management API and not deploy an
OpenAPI-described API for the connector to auto-discover.

The workflow:
1. Provider setup: Create an asset, policy, and contract definition
   on the provider connector via its Management API, pointing to an
   external HTTP data source (jsonplaceholder.typicode.com).
2. Consumer flow: Discover the asset via catalog query, negotiate a
   contract, initiate a pull transfer, receive credentials via SSE,
   and make the final authenticated HTTP request.

Designed to run against the existing dev-up environment.
Uses the SSE-based credential delivery (same as example_pull_sse.py).

**Required environment variables** (from dev-config/.env.dev.consumer):
- EDC_CONNECTOR_HOST
- EDC_CONNECTOR_CONNECTOR_ID
- EDC_CONNECTOR_PARTICIPANT_ID
- EDC_CONNECTOR_MANAGEMENT_PORT
- EDC_CONNECTOR_API_KEY
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

from edcpy.edc_api import (
    ConnectorController,
    create_asset,
    create_contract_definition,
    create_policy_definition,
)

_logger = logging.getLogger(__name__)


@environ.config(prefix="")
class WorkflowConfig:
    """Configuration for the API workflow example."""

    # Provider Management API (accessed from the host)
    provider_management_url: str = environ.var(
        default="http://localhost:19193/management"
    )
    provider_api_key: str = environ.var(default="datacellar")
    provider_api_key_header: str = environ.var(default="X-API-Key")

    # Consumer connector details (set via EDC_CONNECTOR_* env vars
    # from .env.dev.consumer, used by ConnectorController)
    counter_party_protocol_url: str = environ.var(
        default="http://host.docker.internal:19194/protocol"
    )
    counter_party_connector_id: str = environ.var(default="example-provider")

    # Consumer backend SSE endpoint
    consumer_backend_url: str = environ.var(default="http://localhost:28000")
    api_auth_key: str = environ.var(name="EDC_CONNECTOR_API_KEY")

    # Asset configuration
    asset_id: str = environ.var(default="api-workflow-users")
    data_source_url: str = environ.var(default="https://jsonplaceholder.typicode.com")
    data_source_path: str = environ.var(default="/users")

    # Logging
    log_level: str = environ.var(default="DEBUG")


class SSEPullCredentialsReceiver:
    """Receives pull credentials from the consumer backend SSE endpoint.

    Copied from example_pull_sse.py — starts listening *before* the
    transfer is initiated so that the credential message is never missed.
    """

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_auth_key}",
            "Accept": "text/event-stream",
        }
        self._futures: Dict[str, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._connected_event: asyncio.Event = asyncio.Event()

    async def start_listening(self, protocol_url: str):
        if self._listener_task and not self._listener_task.done():
            _logger.warning("SSE listener already running")
            return

        provider_host = urlparse(protocol_url).hostname
        url = f"{self.config.consumer_backend_url}/pull/stream/provider/{provider_host}"

        _logger.info("Connecting to SSE stream for provider: %s", provider_host)
        self._connected_event.clear()
        self._listener_task = asyncio.create_task(self._listen_sse_stream(url))

        await asyncio.wait_for(self._connected_event.wait(), timeout=5)

    async def _listen_sse_stream(self, url: str):
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
                            message = json.loads(line.strip()[6:])
                        except json.JSONDecodeError:
                            _logger.warning("Invalid JSON in SSE message: %s", line)
                            continue

                        if message.get("type") != "pull_message":
                            continue

                        transfer_id = message.get("transfer_process_id")
                        if not transfer_id:
                            continue

                        future = self._futures.get(transfer_id)
                        if future is None:
                            future = asyncio.get_event_loop().create_future()
                            self._futures[transfer_id] = future

                        if not future.done():
                            _logger.info(
                                "Received credentials for transfer: %s", transfer_id
                            )
                            future.set_result(message)

        except Exception as e:
            self._connected_event.set()
            _logger.error("SSE listener error: %s", e)

    async def get_credentials(self, transfer_id: str, timeout: float = 60.0) -> dict:
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
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._futures.clear()
        self._connected_event.clear()


async def setup_provider_assets(config: WorkflowConfig):
    """Create asset, policy, and contract definition on the provider via Management API.

    This is the provider-side setup that would normally be done by the
    OpenAPI auto-generator. Here we do it manually to demonstrate that
    an external actor can register data offerings directly.
    """

    provider_url = config.provider_management_url

    _logger.info("Setting up provider assets via Management API at %s", provider_url)

    # Step 1: Create the asset pointing to the external data source
    _logger.info("Creating asset '%s' → %s", config.asset_id, config.data_source_url)

    asset_data = await create_asset(
        management_url=provider_url,
        config=_build_provider_config(config),
        source_base_url=config.data_source_url,
        source_method="GET",
        uid=config.asset_id,
        proxy_body=True,
        proxy_path=True,
        proxy_query_params=True,
        proxy_method=False,
    )

    _logger.info("Asset created:\n%s", pprint.pformat(asset_data))

    # Step 2: Create an open policy (no restrictions)
    policy_id = f"{config.asset_id}-policy"
    _logger.info("Creating policy '%s'", policy_id)

    policy_data = await create_policy_definition(
        management_url=provider_url,
        config=_build_provider_config(config),
        uid=policy_id,
    )

    _logger.info("Policy created:\n%s", pprint.pformat(policy_data))

    # Step 3: Create a contract definition linking the policy to the asset
    contract_def_id = f"{config.asset_id}-contract"
    _logger.info("Creating contract definition '%s'", contract_def_id)

    contract_def_data = await create_contract_definition(
        management_url=provider_url,
        config=_build_provider_config(config),
        policy_definition_id=policy_id,
        uid=contract_def_id,
    )

    _logger.info("Contract definition created:\n%s", pprint.pformat(contract_def_data))

    return {
        "asset_id": config.asset_id,
        "policy_id": policy_id,
        "contract_def_id": contract_def_id,
    }


async def consume_asset(config: WorkflowConfig):
    """Consumer-side flow: discover, negotiate, pull, and fetch data via SSE.

    This follows the same pattern as example_pull_sse.py, but consuming
    the asset we created via the Management API.
    """

    sse_receiver = SSEPullCredentialsReceiver(config)
    controller = ConnectorController()

    try:
        # Step 1: Start SSE listener *before* negotiation
        await sse_receiver.start_listening(config.counter_party_protocol_url)

        # Step 2: Negotiate contract for the API-created asset
        _logger.info(
            "Negotiating contract for asset '%s' with provider '%s'",
            config.asset_id,
            config.counter_party_connector_id,
        )

        transfer_details = await controller.run_negotiation_flow(
            counter_party_protocol_url=config.counter_party_protocol_url,
            counter_party_connector_id=config.counter_party_connector_id,
            asset_query=config.asset_id,
        )

        _logger.info(
            "Contract negotiated (agreement_id=%s)",
            transfer_details.contract_agreement_id,
        )

        # Step 3: Start pull transfer — credentials arrive via SSE
        transfer_id = await controller.run_transfer_flow(
            transfer_details=transfer_details, is_provider_push=False
        )

        _logger.info("Pull transfer started: %s", transfer_id)

        # Step 4: Receive credentials via SSE and make HTTP request
        pull_message = await sse_receiver.get_credentials(transfer_id)

        _logger.info(
            "Received pull credentials:\n%s",
            pprint.pformat(pull_message["request_args"]),
        )

        async with httpx.AsyncClient() as http_client:
            # The asset was created with proxyPath=true, so we append
            # the desired sub-path to the data-plane proxy URL.
            request_args = pull_message["request_args"].copy()
            request_args["url"] = (
                request_args["url"].rstrip("/") + config.data_source_path
            )

            response = await http_client.request(**request_args)
            data = response.json()

            _logger.info(
                "Response received (%d items):\n%s",
                len(data) if isinstance(data, list) else 1,
                pprint.pformat(data[:2] if isinstance(data, list) else data),
            )

            return data

    finally:
        await sse_receiver.stop_listening()


def _build_provider_config(config: WorkflowConfig):
    """Build an AppConfig-like object for authenticating with the provider Management API."""

    class _ProviderConfig:
        """Minimal config to authenticate against the provider Management API."""

        def __init__(self, api_key, api_key_header):
            self.connector = type(
                "Connector", (), {"api_key": api_key, "api_key_header": api_key_header}
            )()

    return _ProviderConfig(config.provider_api_key, config.provider_api_key_header)


async def main(config: WorkflowConfig):
    """Run the full API-based workflow: provider setup then consumer pull."""

    _logger.info("EDC Management API Workflow Example")

    # Phase 1: Provider-side setup via Management API
    _logger.info("Phase 1: Setting up provider assets via Management API")

    try:
        provider_result = await setup_provider_assets(config)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            _logger.warning(
                "Assets already exist (409 Conflict). "
                "This is expected if the example was run before. "
                "Proceeding with existing assets."
            )
            provider_result = {
                "asset_id": config.asset_id,
                "policy_id": f"{config.asset_id}-policy",
                "contract_def_id": f"{config.asset_id}-contract",
            }
        else:
            raise

    _logger.info("Provider setup complete: %s", provider_result)

    # Phase 2: Consumer-side pull flow via SSE
    _logger.info("Phase 2: Consumer pull workflow (SSE)")

    data = await consume_asset(config)

    _logger.info("Workflow completed successfully!")

    return data


if __name__ == "__main__":
    config: WorkflowConfig = WorkflowConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
