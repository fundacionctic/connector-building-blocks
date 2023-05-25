import logging
import pprint

import coloredlogs
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


@app.post("/")
async def root(item: EndpointDataReference):
    _logger.info("Received EndpointDataReference:\n%s", pprint.pformat(item.dict()))
    return item
