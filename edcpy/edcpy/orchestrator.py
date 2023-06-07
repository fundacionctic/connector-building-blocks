import logging
import pprint
import time

import requests

from edcpy.config import ConsumerProviderPairConfig
from edcpy.models.asset import Asset
from edcpy.models.contract_definition import ContractDefinition
from edcpy.models.contract_negotiation import ContractNegotiation
from edcpy.models.data_plane_instance import DataPlaneInstance
from edcpy.models.policy_definition import PolicyDefinition
from edcpy.models.transfer_process import TransferProcess
from edcpy.utils import join_url

_logger = logging.getLogger(__name__)


def _log_req(method, url, data=None):
    _logger.debug("-> %s %s\n%s", method, url, pprint.pformat(data) if data else "")


def _log_res(method, url, data):
    _logger.debug("<- %s %s\n%s", method, url, pprint.pformat(data))


class RequestOrchestrator:
    DEFAULT_HEADERS = {"Content-Type": "application/json"}

    def __init__(self, config: ConsumerProviderPairConfig) -> None:
        self.config = config

    @classmethod
    def get_catalog_policy(cls, catalog: dict) -> dict:
        dataset = (
            catalog["dcat:dataset"][0]
            if isinstance(catalog["dcat:dataset"], list)
            else catalog["dcat:dataset"]
        )

        policy = (
            dataset["odrl:hasPolicy"][0]
            if isinstance(dataset["odrl:hasPolicy"], list)
            else dataset["odrl:hasPolicy"]
        )

        return policy

    @classmethod
    def get_catalog_contract_offer_id(cls, catalog: dict) -> str:
        return cls.get_catalog_policy(catalog=catalog)["@id"]

    @classmethod
    def get_catalog_asset_id(cls, catalog: dict) -> str:
        return cls.get_catalog_policy(catalog=catalog)["odrl:target"]

    def fetch_provider_catalog_from_consumer(self) -> dict:
        data = {
            "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
            "providerUrl": self.config.provider_protocol_url,
            "protocol": "dataspace-protocol-http",
        }

        url = join_url(self.config.consumer_management_url, "v2/catalog/request")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def _register_data_plane(self, management_url, control_url, public_api_url) -> dict:
        data = DataPlaneInstance.build(
            control_url=control_url, public_api_url=public_api_url
        )

        url = join_url(management_url, "instances")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        response.raise_for_status()

        return data

    def register_consumer_data_plane(self) -> dict:
        return self._register_data_plane(
            management_url=self.config.consumer_management_url,
            control_url=self.config.consumer_control_url,
            public_api_url=self.config.consumer_public_url,
        )

    def register_provider_data_plane(self) -> dict:
        return self._register_data_plane(
            management_url=self.config.provider_management_url,
            control_url=self.config.provider_control_url,
            public_api_url=self.config.provider_public_url,
        )

    def create_provider_http_data_asset(
        self,
        base_url: str,
        path: str,
        method: str,
        content_type: str = "application/json",
    ) -> dict:
        data = Asset.build_http_data(
            source_base_url=base_url,
            source_path=path,
            source_method=method,
            source_content_type=content_type,
        )

        url = join_url(self.config.provider_management_url, "v2/assets")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def create_provider_policy_definition(self) -> dict:
        data = PolicyDefinition.build()

        url = join_url(self.config.provider_management_url, "v2/policydefinitions")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def create_provider_contract_definition(self, policy_definition_id: str) -> dict:
        data = ContractDefinition.build(policy_definition_id=policy_definition_id)

        url = join_url(self.config.provider_management_url, "v2/contractdefinitions")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def create_contract_negotiation_from_consumer(
        self, offer_id: str, asset_id: str
    ) -> dict:
        data = ContractNegotiation.build(
            connector_id=self.config.provider_connector_id,
            connector_ids_url=self.config.provider_protocol_url,
            consumer_id=self.config.consumer_participant_id,
            provider_id=self.config.provider_participant_id,
            offer_id=offer_id,
            asset_id=asset_id,
        )

        url = join_url(self.config.consumer_management_url, "v2/contractnegotiations")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def wait_for_consumer_contract_agreement_id(
        self, contract_negotiation_id: str, iter_sleep: float = 1.0
    ) -> str:
        url = join_url(
            self.config.consumer_management_url,
            f"v2/contractnegotiations/{contract_negotiation_id}",
        )

        while True:
            _log_req("GET", url)
            response = requests.get(url, headers=self.DEFAULT_HEADERS)
            resp_json = response.json()
            _log_res("GET", url, resp_json)

            agreement_id = resp_json.get("edc:contractAgreementId")
            state = resp_json.get("edc:state")

            if state in ["FINALIZED", "VERIFIED"] and agreement_id is not None:
                return agreement_id

            _logger.debug("Waiting for contract agreement id")
            time.sleep(iter_sleep)

    def create_provider_push_transfer_process(
        self,
        contract_agreement_id: str,
        asset_id: str,
        sink_base_url: str,
        sink_path: str,
        sink_method: str = "POST",
        sink_content_type: str = "application/json",
    ) -> dict:
        data = TransferProcess.build_for_provider_http_push(
            connector_id=self.config.provider_connector_id,
            connector_ids_url=self.config.provider_protocol_url,
            contract_agreement_id=contract_agreement_id,
            asset_id=asset_id,
            sink_base_url=sink_base_url,
            sink_path=sink_path,
            sink_method=sink_method,
            sink_content_type=sink_content_type,
        )

        url = join_url(self.config.consumer_management_url, "v2/transferprocesses")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def create_consumer_pull_transfer_process(
        self, contract_agreement_id: str, asset_id: str
    ) -> dict:
        data = TransferProcess.build_for_consumer_http_pull(
            connector_id=self.config.provider_connector_id,
            connector_ids_url=self.config.provider_protocol_url,
            contract_agreement_id=contract_agreement_id,
            asset_id=asset_id,
        )

        url = join_url(self.config.consumer_management_url, "v2/transferprocesses")
        _log_req("POST", url, data)
        response = requests.post(url, headers=self.DEFAULT_HEADERS, json=data)
        resp_json = response.json()
        _log_res("POST", url, resp_json)

        return resp_json

    def wait_for_transfer_process(
        self, transfer_process_id: str, iter_sleep: float = 1.0
    ) -> None:
        url = join_url(
            self.config.consumer_management_url,
            f"v2/transferprocesses/{transfer_process_id}",
        )

        while True:
            _log_req("GET", url)
            response = requests.get(url, headers=self.DEFAULT_HEADERS)
            resp_json = response.json()
            _log_res("GET", url, resp_json)

            if resp_json.get("edc:state") == "COMPLETED":
                return resp_json

            _logger.debug("Waiting for transfer process")
            time.sleep(iter_sleep)
