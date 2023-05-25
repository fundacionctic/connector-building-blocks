import json
import logging
import pprint

import coloredlogs
import jwt
from fastapi import FastAPI
from pydantic import BaseModel

coloredlogs.install(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = FastAPI()


class EndpointDataReference(BaseModel):
    id: str
    endpoint: str
    authKey: str
    authCode: str
    properties: dict


def _decode_endpoint_data_ref(item: EndpointDataReference) -> dict:
    ret = jwt.decode(item.authCode, options={"verify_signature": False})

    ret["dad"] = json.loads(ret["dad"])

    ret["dad"]["properties"]["authCode"] = jwt.decode(
        ret["dad"]["properties"]["authCode"],
        options={"verify_signature": False},
    )

    return ret


@app.post("/")
async def root(item: EndpointDataReference):
    _logger.info(
        "Received %s:\n%s",
        EndpointDataReference,
        pprint.pformat(item.dict()),
    )

    decoded = _decode_endpoint_data_ref(item)

    _logger.info(
        "Decoded %s:\n%s",
        EndpointDataReference,
        pprint.pformat(decoded),
    )

    return item
