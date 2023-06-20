import argparse
import asyncio
import logging
import pprint

from edcpy.config import ConsumerProviderPairConfig
from edcpy.orchestrator import CatalogContent, RequestOrchestrator

_DEFAULT_PULL_BASE_URL = "https://jsonplaceholder.typicode.com"
_DEFAULT_PULL_PATH = "/users"
_DEFAULT_PULL_METHOD = "GET"

_DEFAULT_PUSH_BASE_URL = "http://consumer_backend:8000"
_DEFAULT_PUSH_PATH = "/log"
_DEFAULT_PUSH_METHOD = "POST"


_logger = logging.getLogger(__name__)


def get_env_config() -> ConsumerProviderPairConfig:
    return ConsumerProviderPairConfig.from_env()


async def _run_http_pull_sample(
    source_base_url: str = _DEFAULT_PULL_BASE_URL,
    source_path: str = _DEFAULT_PULL_PATH,
    source_method: str = _DEFAULT_PULL_METHOD,
):
    """Runs an end-to-end example to demonstrate the Eclipse Dataspace Connector HTTP pull pattern.
    This sample is based on the HTTP pull connector from the EDC samples repository."""

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)

    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    await orchestrator.register_provider_data_plane()
    await orchestrator.register_consumer_data_plane()

    asset = await orchestrator.create_provider_http_data_asset(
        base_url=source_base_url, path=source_path, method=source_method
    )

    asset_id = asset["@id"]
    _logger.info(f"Asset ID: {asset_id}")

    policy_def = await orchestrator.create_provider_policy_definition()

    policy_definition_id = policy_def["@id"]
    _logger.info(f"Policy Definition ID: {policy_definition_id}")

    await orchestrator.create_provider_contract_definition(
        policy_definition_id=policy_definition_id
    )

    transfer_details = await orchestrator.prepare_to_transfer_asset(asset_query=None)
    assert transfer_details.asset_id == asset_id

    transfer_process = await orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )


def run_http_pull_sample(*args, **kwargs):
    asyncio.run(_run_http_pull_sample(*args, **kwargs))


async def _run_http_push_sample(
    sink_base_url: str = _DEFAULT_PUSH_BASE_URL,
    sink_path: str = _DEFAULT_PUSH_PATH,
    sink_method: str = _DEFAULT_PUSH_METHOD,
):
    """Runs an end-to-end example to demonstrate the Eclipse Dataspace Connector HTTP push pattern.
    This sample is based on a custom connector that takes care of creating
    the data plane, asset, contract definition and policy definition."""

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)

    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    transfer_details = await orchestrator.prepare_to_transfer_asset(asset_query=None)

    transfer_process = await orchestrator.create_provider_push_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
        sink_base_url=sink_base_url,
        sink_path=sink_path,
        sink_method=sink_method,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )


def run_http_push_sample(*args, **kwargs):
    asyncio.run(_run_http_push_sample(*args, **kwargs))


async def _list_assets():
    """A command line utility to list all assets that are available."""

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)
    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))
    catalog = await orchestrator.fetch_provider_catalog_from_consumer()
    catalog_content = CatalogContent(catalog)
    _logger.info("Found datasets:\n%s", pprint.pformat(list(catalog_content.datasets)))


def list_assets(*args, **kwargs):
    asyncio.run(_list_assets(*args, **kwargs))


async def _http_pull():
    """A command line utility to create a transfer process
    for an arbitrary asset using the HTTP pull pattern."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--asset",
        type=str,
        help="The approximate name of the asset to transfer",
        required=True,
    )

    args = parser.parse_args()

    _logger.info("Running HTTP pull with arguments: %s", args)

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)

    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    transfer_details = await orchestrator.prepare_to_transfer_asset(
        asset_query=args.asset
    )

    transfer_process = await orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )


def http_pull(*args, **kwargs):
    asyncio.run(_http_pull(*args, **kwargs))
