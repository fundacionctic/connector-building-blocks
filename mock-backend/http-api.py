import asyncio
import logging
import os
import pprint
import random
import uuid
from datetime import date, datetime
from typing import Any, Dict, List

import arrow
import coloredlogs
from fastapi import FastAPI, Request
from pydantic import BaseModel

coloredlogs.install(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mock Backend HTTP API",
    description=(
        "A mock API that serves as an example of how to"
        " integrate a service or dataset with the OpenAPI extension of the connector"
    ),
    version="0.0.1",
    contact={
        "name": "Andrés García Mangas",
        "url": "https://github.com/agmangas",
        "email": "andres.garcia@fundacionctic.org",
    },
)


class ElectricityConsumptionPredictionRequest(BaseModel):
    date_from: datetime
    date_to: datetime
    location: str


class ElectricityConsumptionSample(BaseModel):
    date: datetime
    value: int


class ElectrictyConsumptionData(BaseModel):
    location: str
    results: List[ElectricityConsumptionSample]


_PRESENTATION_DEFINITION_EXT = "x-connector-presentation-definition"


def _build_presentation_definition() -> Dict[str, Any]:
    """
    Builds an example Presentation Definition as defined by the DIF Presentation Exchange spec:
    https://identity.foundation/presentation-exchange/spec/v2.0.0/#presentation-definition
    Presentation Definitions are defined in API endpoints to impose authorization
    constraints based on Verifiable Credentials.
    """

    return {
        "id": str(uuid.uuid4()),
        "input_descriptors": [
            {
                "id": "datacellar-credential",
                "name": "The specific type of VC for Data Cellar",
                "purpose": (
                    "This is a simple example of how to declare the types of VCs "
                    "that the connector expects to allow access to this endpoint."
                ),
                "constraints": {
                    "fields": [
                        {
                            "path": ["$.type"],
                            "filter": {
                                "type": "string",
                                "pattern": "DataCellarCredential",
                            },
                        }
                    ]
                },
            }
        ],
    }


def _get_openapi_extra() -> Dict[str, Any]:
    if not bool(os.getenv("ENABLE_PRESENTATION_DEFINITION", False)):
        return {}

    return {_PRESENTATION_DEFINITION_EXT: _build_presentation_definition()}


@app.post(
    "/consumption/prediction",
    tags=["Electricity consumption"],
    openapi_extra=_get_openapi_extra(),
)
async def run_consumption_prediction(
    body: ElectricityConsumptionPredictionRequest,
) -> ElectrictyConsumptionData:
    """Run the ML model for prediction of electricity consumption for the given time period."""

    await asyncio.sleep(random.random())

    arrow_from = arrow.get(body.date_from)
    arrow_to = arrow.get(body.date_to)

    results = [
        {"date": item.isoformat(), "value": random.randint(0, 100)}
        for item in arrow.Arrow.range(
            "hour",
            arrow_from.clone().floor("minute"),
            arrow_to.clone().floor("minute"),
        )
    ]

    return ElectrictyConsumptionData(location=body.location, results=results)


@app.get(
    "/consumption",
    tags=["Electricity consumption"],
    openapi_extra=_get_openapi_extra(),
)
async def get_consumption_data(
    location: str = "Asturias", day: date = None
) -> ElectrictyConsumptionData:
    """Fetch the historical time series of electricity consumption for a given day."""

    await asyncio.sleep(random.random())

    arrow_day = arrow.get(day) if day else arrow.utcnow().shift(days=-1).floor("day")

    results = [
        {"date": item.isoformat(), "value": random.randint(0, 100)}
        for item in arrow.Arrow.range(
            "hour", arrow_day.clone().floor("day"), arrow_day.clone().ceil("day")
        )
    ]

    return ElectrictyConsumptionData(location=location, results=results)


@app.post("/dummy")
async def process_data(request_body: dict):
    """Dummy endpoint that just logs the received data and returns a dummy response."""

    _logger.info("Received POST data:\n%s", pprint.pformat(request_body))
    return {"message": "OK"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    headers = request.headers
    _logger.info("Request headers:\n%s", headers)
    response = await call_next(request)
    return response
