import asyncio
import logging
import pprint
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Union

import httpx

from edcpy.config import AppConfig, ConnectorUrls, get_config
from edcpy.models.asset import Asset
from edcpy.models.contract_definition import ContractDefinition
from edcpy.models.contract_negotiation import ContractNegotiation
from edcpy.models.data_plane_instance import DataPlaneInstance
from edcpy.models.policy_definition import PolicyDefinition
from edcpy.models.transfer_process import TransferProcess
from edcpy.utils import join_url

_DEFAULT_TIMEOUT_SECS = 60

_logger = logging.getLogger(__name__)


def _log_req(method, url, data=None):
    _logger.debug("-> %s %s\n%s", method, url, pprint.pformat(data) if data else "")


def _log_res(method, url, data):
    _logger.debug("<- %s %s\n%s", method, url, pprint.pformat(data))


async def register_data_plane(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    **dataplane_kwargs: Dict[str, Any],
) -> dict:
    data = DataPlaneInstance.build(**dataplane_kwargs)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "dataplanes")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()

    return data


async def create_asset(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    **asset_kwargs: Dict[str, Any],
) -> dict:
    data = Asset.build_http_data(**asset_kwargs)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v3", "assets")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def create_policy_definition(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    **policy_kwargs: Dict[str, Any],
) -> dict:
    data = PolicyDefinition.build(**policy_kwargs)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "policydefinitions")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def create_contract_definition(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    **contract_def_kwargs: Dict[str, Any],
) -> dict:
    data = ContractDefinition.build(**contract_def_kwargs)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "contractdefinitions")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def fetch_catalog(
    management_url: str,
    counter_party_protocol_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
) -> dict:
    data = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "counterPartyAddress": counter_party_protocol_url,
        "protocol": "dataspace-protocol-http",
    }

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "catalog", "request")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def create_contract_negotiation(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    **contract_negotiation_kwargs: Dict[str, Any],
) -> dict:
    data = ContractNegotiation.build(**contract_negotiation_kwargs)

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "contractnegotiations")

        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def wait_for_contract_negotiation(
    management_url: str,
    contract_negotiation_id: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    iter_sleep: float = 1.0,
) -> str:
    url = join_url(
        management_url,
        f"v2/contractnegotiations/{contract_negotiation_id}",
    )

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        while True:
            _log_req("GET", url)
            response = await client.get(url)
            response.raise_for_status()
            resp_json = response.json()
            _log_res("GET", url, resp_json)

            agreement_id = resp_json.get("contractAgreementId")
            state = resp_json.get("state")

            if state in ["FINALIZED", "VERIFIED"] and agreement_id is not None:
                return agreement_id

            _logger.debug(
                "Waiting for contract agreement id (contract_negotiation_id=%s)",
                contract_negotiation_id,
            )

            await asyncio.sleep(iter_sleep)


async def create_transfer_process(
    management_url: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    is_provider_push: bool = False,
    **transfer_process_kwargs: Dict[str, Any],
) -> dict:
    data = (
        TransferProcess.build_for_provider_http_push(**transfer_process_kwargs)
        if is_provider_push
        else TransferProcess.build_for_consumer_http_pull(**transfer_process_kwargs)
    )

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        url = join_url(management_url, "v2", "transferprocesses")
        _log_req("POST", url, data)
        response = await client.post(url, json=data)
        response.raise_for_status()
        resp_json = response.json()
        _log_res("POST", url, resp_json)

    return resp_json


async def wait_for_transfer_process(
    management_url: str,
    transfer_process_id: str,
    timeout_secs: int = _DEFAULT_TIMEOUT_SECS,
    iter_sleep: float = 1.0,
):
    url = join_url(
        management_url,
        f"v2/transferprocesses/{transfer_process_id}",
    )

    async with httpx.AsyncClient(timeout=timeout_secs) as client:
        while True:
            _log_req("GET", url)
            response = await client.get(url)
            response.raise_for_status()
            resp_json = response.json()
            _log_res("GET", url, resp_json)

            if resp_json.get("state") == "COMPLETED":
                return resp_json

            _logger.debug("Waiting for transfer process (id=%s)", transfer_process_id)
            await asyncio.sleep(iter_sleep)


@dataclass
class CatalogContent:
    data: dict

    @property
    def datasets(self) -> Iterator[dict]:
        if not self.data.get("dcat:dataset"):
            return iter([])

        if isinstance(self.data["dcat:dataset"], list):
            return iter(self.data["dcat:dataset"])

        return iter([self.data["dcat:dataset"]])

    def find_one_dataset(self, asset_query: Union[str, None]) -> Union[dict, None]:
        return next(
            (
                dset
                for dset in self.datasets
                if not asset_query
                or asset_query.lower() in dset.get("id", "").lower()
                or asset_query.lower() in dset.get("name", "").lower()
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
        return self.data["@id"]


@dataclass
class TransferProcessDetails:
    asset_id: str
    contract_agreement_id: str
    counter_party_protocol_url: str
    counter_party_connector_id: str


class ConnectorController:
    def __init__(
        self, timeout_secs: int = _DEFAULT_TIMEOUT_SECS, config: AppConfig = None
    ) -> None:
        self.timeout_secs = timeout_secs
        self.config: AppConfig = config or get_config()

    @property
    def connector_urls(self) -> ConnectorUrls:
        return ConnectorUrls(self.config)

    async def fetch_catalog(self, counter_party_protocol_url: str) -> CatalogContent:
        catalog_res = await fetch_catalog(
            management_url=self.connector_urls.management_url,
            counter_party_protocol_url=counter_party_protocol_url,
            timeout_secs=self.timeout_secs,
        )

        return CatalogContent(catalog_res)

    async def run_negotiation_flow(
        self,
        counter_party_protocol_url: str,
        counter_party_connector_id: str,
        asset_query: Union[str, None],
    ) -> TransferProcessDetails:
        _logger.info("Preparing to transfer asset (query: %s)", asset_query)

        catalog_content = await self.fetch_catalog(
            counter_party_protocol_url=counter_party_protocol_url
        )

        dataset_dict = catalog_content.find_one_dataset(asset_query)

        if not dataset_dict:
            raise ValueError(f"Dataset not found for query: {asset_query}")

        _logger.debug("Selected dataset:\n%s", pprint.pformat(dataset_dict))
        dataset = CatalogDataset(data=dataset_dict)
        asset_id = dataset.default_asset_id
        _logger.info("Creating contract negotiation for Asset ID: %s", asset_id)

        # The contract offer needs to be equal to the provider's offer as per the EDC docs

        contract_negotiation = await create_contract_negotiation(
            management_url=self.connector_urls.management_url,
            counter_party_connector_id=counter_party_connector_id,
            counter_party_protocol_url=counter_party_protocol_url,
            asset_id=dataset.default_asset_id,
            policy=dataset.default_policy,
        )

        contract_negotiation_id = contract_negotiation["@id"]
        _logger.debug("Contract Negotiation ID: %s", contract_negotiation_id)

        contract_agreement_id = await wait_for_contract_negotiation(
            management_url=self.connector_urls.management_url,
            contract_negotiation_id=contract_negotiation_id,
        )

        return TransferProcessDetails(
            asset_id=asset_id,
            contract_agreement_id=contract_agreement_id,
            counter_party_protocol_url=counter_party_protocol_url,
            counter_party_connector_id=counter_party_connector_id,
        )

    async def run_transfer_flow(
        self,
        transfer_details: TransferProcessDetails,
        is_provider_push: bool = False,
        **transfer_process_kwargs: Dict[str, Any],
    ) -> str:
        transfer_process = await create_transfer_process(
            management_url=self.connector_urls.management_url,
            is_provider_push=is_provider_push,
            counter_party_connector_id=transfer_details.counter_party_connector_id,
            counter_party_protocol_url=transfer_details.counter_party_protocol_url,
            contract_agreement_id=transfer_details.contract_agreement_id,
            asset_id=transfer_details.asset_id,
            **transfer_process_kwargs,
        )

        transfer_process_id = transfer_process["@id"]

        return transfer_process_id

    async def wait_for_transfer_process(
        self, transfer_process_id: str, **kwargs: Dict[str, Any]
    ):
        await wait_for_transfer_process(
            management_url=self.connector_urls.management_url,
            transfer_process_id=transfer_process_id,
            **kwargs,
        )
