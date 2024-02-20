"""
This example shows how the Consumer can list the assets available in the Provider's catalogue.
"""

import asyncio
import logging
import os
import pprint

import coloredlogs

from edcpy.edc_api import ConnectorController

_ENV_LOG_LEVEL = "LOG_LEVEL"
_ENV_COUNTER_PARTY_PROTOCOL_URL = "COUNTER_PARTY_PROTOCOL_URL"

_logger = logging.getLogger(__name__)


async def main():
    counter_party_protocol_url: str = os.getenv(
        _ENV_COUNTER_PARTY_PROTOCOL_URL, "http://provider.local:9194/protocol"
    )

    controller = ConnectorController()
    _logger.debug("Configuration:\n%s", controller.config)

    catalog = await controller.fetch_catalog(
        counter_party_protocol_url=counter_party_protocol_url
    )

    _logger.info("Found datasets:\n%s", pprint.pformat(list(catalog.datasets)))


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv(_ENV_LOG_LEVEL, "DEBUG"))
    asyncio.run(main())
