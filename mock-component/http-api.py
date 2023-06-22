import asyncio
import logging
import pprint
import random
from datetime import date, datetime
from typing import List

import arrow
import coloredlogs
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

coloredlogs.install(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mock Component",
    description=(
        "A mock API that serves as an example of how to"
        " integrate a component with the Core Connector"
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


@app.post("/consumption/prediction", tags=["Electricity consumption"])
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


@app.get("/consumption", tags=["Electricity consumption"])
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


@app.get("/asyncapi.json", tags=["Event-driven API"])
def get_asyncapi_schema():
    """Returns the AsyncAPI schema that describes the mock event-driven API."""

    return FileResponse("asyncapi.json")


@app.post("/dummy")
async def process_data(request_body: dict):
    """Dummy endpoint that just logs the received data and returns a dummy response."""

    _logger.info("Received POST data:\n%s", pprint.pformat(request_body))
    return {"message": "OK"}
