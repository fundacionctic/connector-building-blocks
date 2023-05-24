import json
import logging
import os
import pprint
import tempfile
import time
import uuid

import requests

_API_KEY = "password"
_APPLICATION_JSON = "application/json"
_CONSUMER_MANAGEMENT_URL = "http://localhost:9192/api/v1/management/"
_PROVIDER_URL = "http://localhost:8282/api/v1/ids/data"
_DEFAULT_HEADERS = {"Content-Type": _APPLICATION_JSON, "X-Api-Key": _API_KEY}
_TMPL_CONTRACT_NEGOTIATION = "contract-negotiation.json"
_TMPL_TRANSFER_PROCESS = "transfer-process.json"

_logger = logging.getLogger(__name__)


def read_template(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fh:
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


def get_catalog():
    url = join_url(_CONSUMER_MANAGEMENT_URL, "catalog/request")
    data = {"providerUrl": _PROVIDER_URL}
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_json(f"POST {url}", resp_json)
    return resp_json


def create_contract_negotiation(asset_id, offer_id):
    data = read_template(_TMPL_CONTRACT_NEGOTIATION)
    data["offer"]["assetId"] = asset_id
    data["offer"]["policy"]["permissions"][0]["target"] = asset_id
    data["offer"]["asset"]["properties"]["asset:prop:id"] = asset_id
    data["offer"]["policy"]["uid"] = str(uuid.uuid4())
    data["offer"]["offerId"] = offer_id

    log_json("Contract negotiation body", data)

    url = join_url(_CONSUMER_MANAGEMENT_URL, "contractnegotiations")
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_json(f"POST ${url}", resp_json)
    return resp_json


def wait_for_contract_agreement_id(cn_id, iter_sleep=2):
    url = join_url(_CONSUMER_MANAGEMENT_URL, f"contractnegotiations/{cn_id}")

    while True:
        response = requests.get(url, headers=_DEFAULT_HEADERS)
        resp_json = response.json()
        log_json(f"GET {url}", resp_json)

        if resp_json.get("contractAgreementId"):
            return resp_json["contractAgreementId"]

        _logger.info("Waiting for contract agreement id...")
        time.sleep(iter_sleep)


def create_transfer_process(agreement_id, asset_id):
    temp_dir = tempfile.gettempdir()
    dest_path = os.path.join(temp_dir, "edc-sample-{}.json".format(int(time.time())))
    _logger.info("Destination file path: %s", dest_path)

    data = read_template(_TMPL_TRANSFER_PROCESS)
    data["assetId"] = asset_id
    data["contractId"] = agreement_id
    data["dataDestination"]["properties"]["path"] = dest_path

    log_json("Transfer process body", data)

    url = join_url(_CONSUMER_MANAGEMENT_URL, "transferprocess")
    response = requests.post(url, headers=_DEFAULT_HEADERS, json=data)
    resp_json = response.json()
    log_json(f"POST {url}", resp_json)
    return resp_json


def main():
    catalog = get_catalog()
    offer = catalog["contractOffers"][0]
    offer_id = offer["id"]
    asset_id = offer["asset"]["id"]
    negotation = create_contract_negotiation(asset_id=asset_id, offer_id=offer_id)
    _logger.info("Contract negotation id: %s", negotation["id"])
    agreement_id = wait_for_contract_agreement_id(cn_id=negotation["id"])
    _logger.info("Contract agreement id: %s", agreement_id)
    create_transfer_process(agreement_id=agreement_id, asset_id=asset_id)


if __name__ == "__main__":
    init_logging()
    main()
