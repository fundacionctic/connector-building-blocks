import json
import logging
import os
import pprint
import time
import uuid

import requests

_API_KEY = "password"
_APPLICATION_JSON = "application/json"
_CONSUMER_MANAGEMENT_URL = "http://localhost:9192/api/v1/management/"
_PROVIDER_URL = "http://localhost:8282/api/v1/ids/data"
_DEFAULT_HEADERS = {"Content-Type": _APPLICATION_JSON, "X-Api-Key": _API_KEY}

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


def build_contract_negotiation(catalog):
    offer = catalog["contractOffers"][0]
    asset_id = offer["asset"]["id"]

    body = read_template("contract-negotiation.json")
    body["offer"]["assetId"] = asset_id
    body["offer"]["policy"]["permissions"][0]["target"] = asset_id
    body["offer"]["asset"]["properties"]["asset:prop:id"] = asset_id
    body["offer"]["policy"]["uid"] = str(uuid.uuid4())

    log_json("Contract negotiation body", body)

    return body


def create_contract_negotiation(data):
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


def main():
    catalog = get_catalog()
    cn_data = build_contract_negotiation(catalog)
    cn = create_contract_negotiation(cn_data)
    _logger.info("Contract negotation id: %s", cn["id"])
    agreement_id = wait_for_contract_agreement_id(cn["id"])
    _logger.info("Contract agreement id: %s", agreement_id)


if __name__ == "__main__":
    init_logging()
    main()
