import argparse
import logging
import os
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
    prov_conn_id = os.getenv(
        "PROVIDER_CONNECTOR_ID", "urn:connector:datacellar:provider"
    )

    cons_conn_id = os.getenv(
        "CONSUMER_CONNECTOR_ID", "urn:connector:datacellar:consumer"
    )

    return ConsumerProviderPairConfig(
        provider_host=os.getenv("PROVIDER_HOST", "provider").strip(),
        consumer_host=os.getenv("CONSUMER_HOST", "consumer").strip(),
        provider_connector_id=prov_conn_id.strip(),
        consumer_connector_id=cons_conn_id.strip(),
        provider_participant_id=os.getenv(
            "PROVIDER_PARTICIPANT_ID", prov_conn_id
        ).strip(),
        consumer_participant_id=os.getenv(
            "CONSUMER_PARTICIPANT_ID", cons_conn_id
        ).strip(),
        provider_management_port=int(os.getenv("PROVIDER_MANAGEMENT_PORT", None)),
        consumer_management_port=int(os.getenv("CONSUMER_MANAGEMENT_PORT", None)),
        provider_control_port=int(os.getenv("PROVIDER_CONTROL_PORT", None)),
        consumer_control_port=int(os.getenv("CONSUMER_CONTROL_PORT", None)),
        provider_public_port=int(os.getenv("PROVIDER_PUBLIC_PORT", None)),
        consumer_public_port=int(os.getenv("CONSUMER_PUBLIC_PORT", None)),
        provider_protocol_port=int(os.getenv("PROVIDER_PROTOCOL_PORT", None)),
        consumer_protocol_port=int(os.getenv("CONSUMER_PROTOCOL_PORT", None)),
    )


def run_http_pull_sample(
    source_base_url: str = _DEFAULT_PULL_BASE_URL,
    source_path: str = _DEFAULT_PULL_PATH,
    source_method: str = _DEFAULT_PULL_METHOD,
):
    """Runs an end-to-end example to demonstrate the Eclipse Dataspace Connector HTTP pull pattern.
    This sample is based on the HTTP pull connector that is available in the EDC samples repository.
    """

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)

    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    orchestrator.register_provider_data_plane()
    orchestrator.register_consumer_data_plane()

    asset = orchestrator.create_provider_http_data_asset(
        base_url=source_base_url, path=source_path, method=source_method
    )

    asset_id = asset["@id"]
    _logger.info(f"Asset ID: {asset_id}")

    policy_def = orchestrator.create_provider_policy_definition()

    policy_definition_id = policy_def["@id"]
    _logger.info(f"Policy Definition ID: {policy_definition_id}")

    orchestrator.create_provider_contract_definition(
        policy_definition_id=policy_definition_id
    )

    transfer_details = orchestrator.prepare_to_transfer_asset(asset_query=None)
    assert transfer_details.asset_id == asset_id

    transfer_process = orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    orchestrator.wait_for_transfer_process(transfer_process_id=transfer_process_id)


def run_http_push_sample(
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

    transfer_details = orchestrator.prepare_to_transfer_asset(asset_query=None)

    transfer_process = orchestrator.create_provider_push_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
        sink_base_url=sink_base_url,
        sink_path=sink_path,
        sink_method=sink_method,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    orchestrator.wait_for_transfer_process(transfer_process_id=transfer_process_id)


def list_assets():
    """A command line utility to list all assets that are available."""

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)
    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))
    catalog = orchestrator.fetch_provider_catalog_from_consumer()
    catalog_content = CatalogContent(catalog)
    _logger.info("Found datasets:\n%s", pprint.pformat(list(catalog_content.datasets)))


def http_pull():
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

    transfer_details = orchestrator.prepare_to_transfer_asset(asset_query=args.asset)

    transfer_process = orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    orchestrator.wait_for_transfer_process(transfer_process_id=transfer_process_id)
