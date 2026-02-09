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

All configuration is explicitly passed to the ConnectorController and other
components, eliminating reliance on implicit environment variables.

Configuration can be provided via environment variables or loaded from a
dotenv file using the --env-file option. This allows you to easily switch
between different environment configurations.

Usage:
    # Use existing environment variables
    python example_api_workflow.py

    # Load configuration from a dotenv file
    python example_api_workflow.py --env-file ../dev-config/.env.dev.consumer
"""

import argparse
import asyncio
import json
import logging
import os
import pprint
from typing import Dict, Optional
from urllib.parse import urlparse

import coloredlogs
import environ
import httpx

from edcpy.config import AppConfig
from edcpy.edc_api import (
    ConnectorController,
    create_asset,
    create_contract_definition,
    create_policy_definition,
)

_logger = logging.getLogger(__name__)

# Try to import dotenv, but degrade gracefully if not available
try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False
    _logger.debug("python-dotenv not available; --env-file option will be ignored")


@environ.config(prefix="")
class WorkflowConfig:
    """Configuration for the API workflow example.

    All connector configuration is explicitly defined here to avoid
    hidden dependencies on environment variables.
    """

    # Provider Management API (accessed from the host)
    provider_management_url: str = environ.var(
        default="http://localhost:19193/management"
    )
    provider_api_key: str = environ.var(default="datacellar")
    provider_api_key_header: str = environ.var(default="X-API-Key")

    # Consumer connector details
    counter_party_protocol_url: str = environ.var(
        default="http://host.docker.internal:19194/protocol"
    )
    counter_party_connector_id: str = environ.var(default="example-provider")

    # Consumer connector configuration (explicitly defined)
    consumer_scheme: str = environ.var(default="http")
    consumer_host: str = environ.var(default="host.docker.internal")
    consumer_connector_id: str = environ.var(default="example-consumer")
    consumer_participant_id: str = environ.var(default="example-consumer")
    consumer_management_port: int = environ.var(default=29193, converter=int)
    consumer_management_path: str = environ.var(default="/management")
    consumer_control_port: int = environ.var(default=29192, converter=int)
    consumer_control_path: str = environ.var(default="/control")
    consumer_public_port: int = environ.var(default=29291, converter=int)
    consumer_public_path: str = environ.var(default="/public")
    consumer_protocol_port: int = environ.var(default=29194, converter=int)
    consumer_protocol_path: str = environ.var(default="/protocol")
    consumer_api_key: str = environ.var(default="datacellar")
    consumer_api_key_header: str = environ.var(default="X-API-Key")

    # Consumer backend SSE endpoint
    consumer_backend_url: str = environ.var(default="http://host.docker.internal:28000")

    # Asset configuration
    asset_id: str = environ.var(default="example-asset-managed-via-api")
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
            "Authorization": f"Bearer {config.consumer_api_key}",
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
        base_url = self.config.consumer_backend_url.rstrip("/")
        url = f"{base_url}/pull/stream/provider/{provider_host}"

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
    controller = ConnectorController(config=_build_consumer_config(config))

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


def _build_consumer_config(config: WorkflowConfig) -> AppConfig:
    """Build an explicit AppConfig for the consumer connector.

    All configuration values are explicitly provided from WorkflowConfig,
    avoiding any hidden dependencies on environment variables.
    """

    class _ConnectorConfig:
        """Explicit connector configuration."""

        def __init__(
            self,
            scheme: str,
            host: str,
            connector_id: str,
            participant_id: str,
            management_port: int,
            management_path: str,
            control_port: int,
            control_path: str,
            public_port: int,
            public_path: str,
            protocol_port: int,
            protocol_path: str,
            api_key: str,
            api_key_header: str,
        ):
            self.scheme = scheme
            self.host = host
            self.connector_id = connector_id
            self.participant_id = participant_id
            self.management_port = management_port
            self.management_path = management_path
            self.control_port = control_port
            self.control_path = control_path
            self.public_port = public_port
            self.public_path = public_path
            self.protocol_port = protocol_port
            self.protocol_path = protocol_path
            self.api_key = api_key
            self.api_key_header = api_key_header

    class _AppConfig:
        """Explicit AppConfig."""

        def __init__(self, connector: _ConnectorConfig):
            self.connector = connector
            self.cert_path = None
            self.rabbit_url = None
            self.http_api_port = 8000

    connector_config = _ConnectorConfig(
        scheme=config.consumer_scheme,
        host=config.consumer_host,
        connector_id=config.consumer_connector_id,
        participant_id=config.consumer_participant_id,
        management_port=config.consumer_management_port,
        management_path=config.consumer_management_path,
        control_port=config.consumer_control_port,
        control_path=config.consumer_control_path,
        public_port=config.consumer_public_port,
        public_path=config.consumer_public_path,
        protocol_port=config.consumer_protocol_port,
        protocol_path=config.consumer_protocol_path,
        api_key=config.consumer_api_key,
        api_key_header=config.consumer_api_key_header,
    )

    return _AppConfig(connector_config)


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


def parse_args():
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="EDC Management API Workflow Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Configuration:
  Configuration can be provided via environment variables or a dotenv file.
  Use --env-file to load environment variables from a specific file.
  
  Example:
    python example_api_workflow.py --env-file ../dev-config/.env.dev.consumer
        """,
    )

    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to a dotenv file to load environment variables from. "
        "Requires python-dotenv to be installed.",
        metavar="PATH",
    )

    return parser.parse_args()


def load_env_file(env_file_path: str) -> bool:
    """Load environment variables from a dotenv file.

    Args:
        env_file_path: Path to the dotenv file

    Returns:
        True if the file was loaded successfully, False otherwise
    """

    if not _DOTENV_AVAILABLE:
        _logger.warning(
            "Cannot load env file '%s': python-dotenv is not installed. "
            "Install it with: pip install python-dotenv",
            env_file_path,
        )
        return False

    if not os.path.exists(env_file_path):
        _logger.error("Environment file not found: %s", env_file_path)
        return False

    _logger.info("Loading environment variables from: %s", env_file_path)
    load_dotenv(env_file_path, override=True)
    return True


if __name__ == "__main__":
    args = parse_args()

    # Load dotenv file if specified
    if args.env_file:
        load_env_file(args.env_file)

    config: WorkflowConfig = WorkflowConfig.from_environ()
    coloredlogs.install(level=config.log_level)
    asyncio.run(main(config))
