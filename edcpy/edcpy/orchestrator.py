import logging
import pprint
import time
from dataclasses import dataclass
from typing import Iterator, Union

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


@dataclass
class TransferProcessDetails:
    asset_id: str
    contract_agreement_id: str


@dataclass
class CatalogContent:
    data: dict

    @property
    def datasets(self) -> Iterator[dict]:
        if not self.data.get("dcat:dataset"):
            return iter([])
        elif isinstance(self.data["dcat:dataset"], list):
            return iter(self.data["dcat:dataset"])
        else:
            return iter([self.data["dcat:dataset"]])

    def find_one_dataset(self, asset_query: Union[str, None]) -> Union[dict, None]:
        return next(
            (
                dset
                for dset in self.datasets
                if not asset_query
                or asset_query.lower() in dset["edc:id"].lower()
                or asset_query.lower() in dset["edc:name"].lower()
            ),
            None,
        )


@dataclass
class CatalogDataset:
    data: dict

    @property
    def default_policy(self) -> dict:
        return (
            self.data["odrl:hasPolicy"][0]
            if isinstance(self.data["odrl:hasPolicy"], list)
            else self.data["odrl:hasPolicy"]
        )

    @property
    def default_contract_offer_id(self) -> str:
        return self.default_policy["@id"]

    @property
    def default_asset_id(self) -> str:
        return self.default_policy["odrl:target"]


class RequestOrchestrator:
    DEFAULT_HEADERS = {"Content-Type": "application/json"}

    def __init__(self, config: ConsumerProviderPairConfig) -> None:
        self.config = config

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

    def prepare_to_transfer_asset(
        self, asset_query: Union[str, None]
    ) -> TransferProcessDetails:
        _logger.info("Preparing to transfer asset (query: %s)", asset_query)

        catalog = self.fetch_provider_catalog_from_consumer()
        catalog_content = CatalogContent(data=catalog)
        dataset_dict = catalog_content.find_one_dataset(asset_query)
        assert dataset_dict, f"Dataset not found for query: {asset_query}"
        _logger.debug("Selected dataset:\n%s", pprint.pformat(dataset_dict))
        dataset = CatalogDataset(data=dataset_dict)
        contract_offer_id = dataset.default_contract_offer_id
        _logger.debug(f"Contract Offer ID: {contract_offer_id}")
        asset_id = dataset.default_asset_id
        _logger.debug(f"Asset ID: {asset_id}")

        contract_negotiation = self.create_contract_negotiation_from_consumer(
            offer_id=contract_offer_id, asset_id=asset_id
        )

        contract_negotiation_id = contract_negotiation["@id"]
        _logger.debug(f"Contract Negotiation ID: {contract_negotiation_id}")

        contract_agreement_id = self.wait_for_consumer_contract_agreement_id(
            contract_negotiation_id=contract_negotiation_id
        )

        return TransferProcessDetails(
            asset_id=asset_id, contract_agreement_id=contract_agreement_id
        )
