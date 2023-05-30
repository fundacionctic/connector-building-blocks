import asyncio
import logging
import random
from datetime import date, datetime
from typing import List

import arrow
import coloredlogs
from fastapi import FastAPI
from pydantic import BaseModel

coloredlogs.install(level=logging.DEBUG)

app = FastAPI(
    title="Data Cellar Mock Component",
    description=(
        "A mock API that serves as an example of how to"
        " integrate a Data Cellar component with the Data Cellar Core Connector"
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
async def get_consumption_data(location: str, day: date) -> ElectrictyConsumptionData:
    """Fetch the historical time series of electricity consumption for a given day."""

    await asyncio.sleep(random.random())

    arrow_day = arrow.get(day)

    results = [
        {"date": item.isoformat(), "value": random.randint(0, 100)}
        for item in arrow.Arrow.range(
            "hour", arrow_day.clone().floor("day"), arrow_day.clone().ceil("day")
        )
    ]

    return ElectrictyConsumptionData(location=location, results=results)
