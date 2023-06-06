import logging
import os
import pprint
import time

import requests
from deepmerge import Merger

_PROVIDER_HOST = os.getenv("PROVIDER_HOST", "provider")
_CONSUMER_HOST = os.getenv("CONSUMER_HOST", "consumer")

_PROVIDER_CONNECTOR_ID = os.getenv(
    "PROVIDER_CONNECTOR_ID", "urn:connector:datacellar:provider"
)

_CONSUMER_CONNECTOR_ID = os.getenv(
    "CONSUMER_CONNECTOR_ID", "urn:connector:datacellar:consumer"
)

_PROVIDER_PARTICIPANT_ID = os.getenv("PROVIDER_PARTICIPANT_ID", _PROVIDER_CONNECTOR_ID)
_CONSUMER_PARTICIPANT_ID = os.getenv("CONSUMER_PARTICIPANT_ID", _CONSUMER_CONNECTOR_ID)

_CONSUMER_MANAGEMENT_URL = f"http://{_CONSUMER_HOST}:29193/management"
_PROVIDER_IDS_URL = f"http://{_PROVIDER_HOST}:9194/protocol"

_DEFAULT_HEADERS = {"Content-Type": "application/json"}

_logger = logging.getLogger(__name__)

_list_override_merger = Merger(
    [(list, ["override"]), (dict, ["merge"]), (set, ["union"])],
    ["override"],
    ["override"],
)

_contract_negotation_body = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "NegotiationInitiateRequestDto",
    "connectorId": None,
    "consumerId": None,
    "providerId": None,
    "connectorAddress": None,
    "protocol": "dataspace-protocol-http",
    "offer": {
        "offerId": None,
        "assetId": None,
        "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@id": None,
            "@type": "Set",
            "permission": [],
            "prohibition": [],
            "obligation": [],
            "target": None,
        },
    },
}

_transfer_process_body = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "TransferRequestDto",
    "dataDestination": {},
    "protocol": "dataspace-protocol-http",
    "assetId": None,
    "contractId": None,
    "connectorAddress": None,
    "privateProperties": {},
    "managedResources": False,
}


def init_logging():
    try:
        import coloredlogs  # type: ignore

        coloredlogs.install(level="DEBUG")
    except ImportError:
        logging.basicConfig(level=logging.DEBUG)


def log_req(method, url, data=None):
    _logger.debug("-> %s %s\n%s", method, url, pprint.pformat(data) if data else "")


def log_res(method, url, data):
    _logger.debug("<- %s %s\n%s", method, url, pprint.pformat(data))


def join_url(url, path):
    return url + path if url.endswith("/") else url + "/" + path


def fetch_catalog(management_url, provider_ids_url):
    data = {
        "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
        "providerUrl": provider_ids_url,
        "protocol": "dataspace-protocol-http",
    }

    url = join_url(management_url, "v2/catalog/request")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def get_policy(catalog):
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


def get_contract_offer_id(catalog):
    return get_policy(catalog=catalog)["@id"]


def get_asset_id(catalog):
    return get_policy(catalog=catalog)["odrl:target"]


def create_contract_negotiation(
    management_url,
    offer_id,
    asset_id,
    connector_ids_url,
    connector_id,
    consumer_id,
    provider_id,
):
    data = _list_override_merger.merge(
        _contract_negotation_body,
        {
            "connectorId": connector_id,
            "connectorAddress": connector_ids_url,
            "consumerId": consumer_id,
            "providerId": provider_id,
            "offer": {
                "offerId": offer_id,
                "assetId": asset_id,
                "policy": {
                    "@id": offer_id,
                    "target": asset_id,
                },
            },
        },
    )

    url = join_url(management_url, "v2/contractnegotiations")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def wait_for_contract_agreement_id(
    management_url, contract_negotiation_id, iter_sleep=1
):
    url = join_url(management_url, f"v2/contractnegotiations/{contract_negotiation_id}")

    while True:
        log_req("GET", url)
        response = requests.get(url, headers=_DEFAULT_HEADERS)
        resp_json = response.json()
        log_res("GET", url, resp_json)

        agreement_id = resp_json.get("edc:contractAgreementId")
        state = resp_json.get("edc:state")

        if state in ["FINALIZED", "VERIFIED"] and agreement_id is not None:
            return agreement_id

        _logger.debug("Waiting for contract agreement id")
        time.sleep(iter_sleep)


def create_transfer_process(
    management_url, connector_ids_url, asset_id, contract_agreement_id, connector_id
):
    data = _list_override_merger.merge(
        _transfer_process_body,
        {
            "dataDestination": {
                "@type": "DataAddress",
                "type": "HttpData",
                "properties": {
                    "baseUrl": "http://host.docker.internal:9090",
                    "path": "/dummy",
                    "method": "POST",
                    "contentType": "application/json",
                },
            },
            "connectorId": connector_id,
            "connectorAddress": connector_ids_url,
            "contractId": contract_agreement_id,
            "assetId": asset_id,
        },
    )

    url = join_url(management_url, "v2/transferprocesses")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def wait_for_transfer_process(management_url, transfer_process_id, iter_sleep=1):
    url = join_url(management_url, f"v2/transferprocesses/{transfer_process_id}")

    while True:
        log_req("GET", url)
        response = requests.get(url, headers=_DEFAULT_HEADERS)
        resp_json = response.json()
        log_res("GET", url, resp_json)

        if resp_json.get("edc:state") == "COMPLETED":
            return resp_json

        _logger.debug("Waiting for transfer process")
        time.sleep(iter_sleep)


def main():
    provider_catalog = fetch_catalog(
        management_url=_CONSUMER_MANAGEMENT_URL, provider_ids_url=_PROVIDER_IDS_URL
    )

    contract_offer_id = get_contract_offer_id(catalog=provider_catalog)
    asset_id = get_asset_id(catalog=provider_catalog)

    contract_negotiation = create_contract_negotiation(
        management_url=_CONSUMER_MANAGEMENT_URL,
        offer_id=contract_offer_id,
        asset_id=asset_id,
        connector_ids_url=_PROVIDER_IDS_URL,
        connector_id=_PROVIDER_CONNECTOR_ID,
        consumer_id=_CONSUMER_PARTICIPANT_ID,
        provider_id=_PROVIDER_PARTICIPANT_ID,
    )

    contract_negotiation_id = contract_negotiation["@id"]

    contract_agreement_id = wait_for_contract_agreement_id(
        management_url=_CONSUMER_MANAGEMENT_URL,
        contract_negotiation_id=contract_negotiation_id,
    )

    transfer_process = create_transfer_process(
        management_url=_CONSUMER_MANAGEMENT_URL,
        connector_ids_url=_PROVIDER_IDS_URL,
        asset_id=asset_id,
        contract_agreement_id=contract_agreement_id,
        connector_id=_PROVIDER_CONNECTOR_ID,
    )

    transfer_process_id = transfer_process["@id"]

    wait_for_transfer_process(
        management_url=_CONSUMER_MANAGEMENT_URL, transfer_process_id=transfer_process_id
    )


if __name__ == "__main__":
    init_logging()
    main()
