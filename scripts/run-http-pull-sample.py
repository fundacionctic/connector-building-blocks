import json
import logging
import os
import pprint
import time
import uuid

import requests
from deepmerge import Merger

_PROVIDER_MANAGEMENT_URL = "http://localhost:19193/api/v1/data"
_CONSUMER_MANAGEMENT_URL = "http://localhost:29193/api/v1/data"

_PROVIDER_CONTROL_URL = "http://localhost:19192/control"
_CONSUMER_CONTROL_URL = "http://localhost:29192/control"

_PROVIDER_PUBLIC_URL = "http://localhost:19291/public"
_CONSUMER_PUBLIC_URL = "http://localhost:29291/public"

_PROVIDER_IDS_URL = "http://localhost:19194/api/v1/ids"

_APPLICATION_JSON = "application/json"
_DEFAULT_HEADERS = {"Content-Type": _APPLICATION_JSON}
_CONNECTOR_ID = "http-pull-connector"

_logger = logging.getLogger(__name__)

_list_override_merger = Merger(
    [(list, ["override"]), (dict, ["merge"]), (set, ["union"])],
    ["override"],
    ["override"],
)


def read_template(fname):
    with open(
        os.path.join(os.path.dirname(__file__), "http-pull-templates", fname)
    ) as fh:
        return json.loads(fh.read())


def init_logging():
    try:
        import coloredlogs  # type: ignore

        coloredlogs.install(level="DEBUG")
    except ImportError:
        logging.basicConfig(level=logging.DEBUG)


def join_url(url, path):
    return url + path if url.endswith("/") else url + "/" + path


def log_json(descr, content):
    _logger.debug("%s:\n%s", descr, pprint.pformat(content))


def log_req(method, url, data=None):
    _logger.debug("-> %s %s\n%s", method, url, pprint.pformat(data) if data else "")


def log_res(method, url, data):
    _logger.debug("<- %s %s\n%s", method, url, pprint.pformat(data))


def register_data_plane(management_url, control_url, public_url):
    data = read_template("instance.json")

    data = _list_override_merger.merge(
        data,
        {
            "id": "dplane-{}".format(uuid.uuid4()),
            "url": join_url(control_url, "transfer"),
            "properties": {"publicApiUrl": public_url},
        },
    )

    url = join_url(management_url, "instances")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    response.raise_for_status()

    return data


def create_asset(management_url):
    data = read_template("asset.json")

    asset_uid = str(uuid.uuid4())

    data = _list_override_merger.merge(
        data,
        {
            "asset": {
                "properties": {
                    "asset:prop:id": "asset-{}".format(asset_uid),
                    "asset:prop:name": f"Name of asset {asset_uid}",
                }
            },
            "dataAddress": {
                "properties": {
                    "name": f"Data address name of asset {asset_uid}",
                    "baseUrl": "https://jsonplaceholder.typicode.com/users",
                }
            },
        },
    )

    url = join_url(management_url, "assets")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def create_policy_definition(management_url, asset_id):
    data = read_template("policy-definition.json")

    policy_id = "policy-{}".format(uuid.uuid4())
    policy_def_id = "policy-def-{}".format(uuid.uuid4())

    data = _list_override_merger.merge(
        data,
        {
            "id": policy_def_id,
            "policy": {
                "uid": policy_id,
                "permissions": [
                    {**data["policy"]["permissions"][0], **{"target": asset_id}}
                ],
            },
        },
    )

    url = join_url(management_url, "policydefinitions")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json, policy_id


def create_contract_definition(management_url, policy_def_id):
    data = read_template("contract-definition.json")

    contract_def_id = "contract-def-{}".format(uuid.uuid4())

    data = _list_override_merger.merge(
        data,
        {
            "id": contract_def_id,
            "accessPolicyId": policy_def_id,
            "contractPolicyId": policy_def_id,
        },
    )

    url = join_url(management_url, "contractdefinitions")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def fetch_catalog(management_url, provider_ids_url):
    data = {"providerUrl": join_url(provider_ids_url, "data")}
    url = join_url(management_url, "catalog/request")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def create_contract_negotiation(
    management_url, offer_id, asset_id, policy_id, connector_ids_url, connector_id
):
    data = read_template("contract-negotiation.json")

    data = _list_override_merger.merge(
        data,
        {
            "connectorId": connector_id,
            "connectorAddress": join_url(connector_ids_url, "data"),
            "offer": {
                "offerId": offer_id,
                "assetId": asset_id,
                "policy": {
                    "uid": policy_id,
                    "permissions": [
                        {
                            **data["offer"]["policy"]["permissions"][0],
                            **{"target": asset_id},
                        },
                    ],
                },
            },
        },
    )

    url = join_url(management_url, "contractnegotiations")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def wait_for_contract_agreement_id(
    management_url, contract_negotiation_id, iter_sleep=1
):
    url = join_url(management_url, f"contractnegotiations/{contract_negotiation_id}")

    while True:
        log_req("GET", url)
        response = requests.get(url, headers=_DEFAULT_HEADERS)
        resp_json = response.json()
        log_res("GET", url, resp_json)

        if resp_json.get("contractAgreementId"):
            return resp_json["contractAgreementId"]

        _logger.debug("Waiting for contract agreement id")
        time.sleep(iter_sleep)


def create_transfer_process(
    management_url, connector_ids_url, asset_id, contract_agreement_id, connector_id
):
    data = read_template("transfer-process.json")

    data = _list_override_merger.merge(
        data,
        {
            "connectorId": connector_id,
            "connectorAddress": join_url(connector_ids_url, "data"),
            "contractId": contract_agreement_id,
            "assetId": asset_id,
        },
    )

    url = join_url(management_url, "transferprocess")
    log_req("POST", url, data)
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_res("POST", url, resp_json)

    return resp_json


def wait_for_transfer_process(management_url, transfer_process_id, iter_sleep=1):
    url = join_url(management_url, f"transferprocess/{transfer_process_id}")

    while True:
        log_req("GET", url)
        response = requests.get(url, headers=_DEFAULT_HEADERS)
        resp_json = response.json()
        log_res("GET", url, resp_json)

        if resp_json.get("state") == "COMPLETED":
            return resp_json

        _logger.debug("Waiting for transfer process")
        time.sleep(iter_sleep)


def main():
    register_data_plane(
        management_url=_PROVIDER_MANAGEMENT_URL,
        control_url=_PROVIDER_CONTROL_URL,
        public_url=_PROVIDER_PUBLIC_URL,
    )

    register_data_plane(
        management_url=_CONSUMER_MANAGEMENT_URL,
        control_url=_CONSUMER_CONTROL_URL,
        public_url=_CONSUMER_PUBLIC_URL,
    )

    prov_asset = create_asset(management_url=_PROVIDER_MANAGEMENT_URL)
    prov_asset_id = prov_asset["id"]

    prov_policy_def, prov_policy_id = create_policy_definition(
        management_url=_PROVIDER_MANAGEMENT_URL, asset_id=prov_asset_id
    )

    prov_policy_def_id = prov_policy_def["id"]

    create_contract_definition(
        management_url=_PROVIDER_MANAGEMENT_URL, policy_def_id=prov_policy_def_id
    )

    prov_catalog_from_cons = fetch_catalog(
        management_url=_CONSUMER_MANAGEMENT_URL, provider_ids_url=_PROVIDER_IDS_URL
    )

    contract_offer_id = prov_catalog_from_cons["contractOffers"][0]["id"]

    contract_negotiation = create_contract_negotiation(
        management_url=_CONSUMER_MANAGEMENT_URL,
        offer_id=contract_offer_id,
        asset_id=prov_asset_id,
        policy_id=prov_policy_id,
        connector_ids_url=_PROVIDER_IDS_URL,
        connector_id=_CONNECTOR_ID,
    )

    contract_negotiation_id = contract_negotiation["id"]

    contract_agreement_id = wait_for_contract_agreement_id(
        management_url=_CONSUMER_MANAGEMENT_URL,
        contract_negotiation_id=contract_negotiation_id,
    )

    transfer_process = create_transfer_process(
        management_url=_CONSUMER_MANAGEMENT_URL,
        connector_ids_url=_PROVIDER_IDS_URL,
        asset_id=prov_asset_id,
        contract_agreement_id=contract_agreement_id,
        connector_id=_CONNECTOR_ID,
    )

    transfer_process_id = transfer_process["id"]

    wait_for_transfer_process(
        management_url=_CONSUMER_MANAGEMENT_URL, transfer_process_id=transfer_process_id
    )


if __name__ == "__main__":
    init_logging()
    main()
