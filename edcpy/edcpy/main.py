import logging
import os
import pprint

import coloredlogs

from edcpy.config import ConsumerProviderPairConfig
from edcpy.orchestrator import RequestOrchestrator

_logger = logging.getLogger(__name__)


def get_env_config() -> ConsumerProviderPairConfig:
    prov_conn_id = os.getenv(
        "PROVIDER_CONNECTOR_ID", "urn:connector:datacellar:provider"
    )

    cons_conn_id = os.getenv(
        "CONSUMER_CONNECTOR_ID", "urn:connector:datacellar:consumer"
    )

    return ConsumerProviderPairConfig(
        provider_host=os.getenv("PROVIDER_HOST", "provider"),
        consumer_host=os.getenv("CONSUMER_HOST", "consumer"),
        provider_connector_id=prov_conn_id,
        consumer_connector_id=cons_conn_id,
        provider_participant_id=os.getenv("PROVIDER_PARTICIPANT_ID", prov_conn_id),
        consumer_participant_id=os.getenv("CONSUMER_PARTICIPANT_ID", cons_conn_id),
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
    source_base_url: str = "https://jsonplaceholder.typicode.com",
    source_path: str = "/users",
    source_method: str = "GET",
):
    coloredlogs.install(level=logging.DEBUG)

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

    catalog = orchestrator.fetch_provider_catalog_from_consumer()

    contract_offer_id = RequestOrchestrator.get_catalog_contract_offer_id(catalog)
    _logger.info(f"Contract Offer ID: {contract_offer_id}")

    contract_negotiation = orchestrator.create_contract_negotiation_from_consumer(
        offer_id=contract_offer_id, asset_id=asset_id
    )

    contract_negotiation_id = contract_negotiation["@id"]
    _logger.info(f"Contract Negotiation ID: {contract_negotiation_id}")

    contract_agreement_id = orchestrator.wait_for_consumer_contract_agreement_id(
        contract_negotiation_id=contract_negotiation_id
    )

    transfer_process = orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=contract_agreement_id, asset_id=asset_id
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    orchestrator.wait_for_transfer_process(transfer_process_id=transfer_process_id)


def run_http_push_sample(
    sink_base_url: str = "http://consumer_backend:8000",
    sink_path: str = "/log",
    sink_method: str = "POST",
):
    coloredlogs.install(level=logging.DEBUG)

    config = get_env_config()
    orchestrator = RequestOrchestrator(config=config)

    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

    catalog = orchestrator.fetch_provider_catalog_from_consumer()

    contract_offer_id = RequestOrchestrator.get_catalog_contract_offer_id(catalog)
    _logger.info(f"Contract Offer ID: {contract_offer_id}")

    asset_id = RequestOrchestrator.get_catalog_asset_id(catalog)
    _logger.info(f"Asset ID: {asset_id}")

    contract_negotiation = orchestrator.create_contract_negotiation_from_consumer(
        offer_id=contract_offer_id, asset_id=asset_id
    )

    contract_negotiation_id = contract_negotiation["@id"]
    _logger.info(f"Contract Negotiation ID: {contract_negotiation_id}")

    contract_agreement_id = orchestrator.wait_for_consumer_contract_agreement_id(
        contract_negotiation_id=contract_negotiation_id
    )

    transfer_process = orchestrator.create_provider_push_transfer_process(
        contract_agreement_id=contract_agreement_id,
        asset_id=asset_id,
        sink_base_url=sink_base_url,
        sink_path=sink_path,
        sink_method=sink_method,
    )

    transfer_process_id = transfer_process["@id"]
    _logger.info(f"Transfer Process ID: {transfer_process_id}")

    orchestrator.wait_for_transfer_process(transfer_process_id=transfer_process_id)
