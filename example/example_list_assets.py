"""
This example shows how the Consumer can list the assets available in the Provider's catalogue.
"""

import asyncio
import logging
import os
import pprint

import coloredlogs

from edcpy.config import ConsumerProviderPairConfig
from edcpy.orchestrator import CatalogContent, RequestOrchestrator

_logger = logging.getLogger(__name__)


async def main():
    config = ConsumerProviderPairConfig.from_env()
    orchestrator = RequestOrchestrator(config=config)
    _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))
    catalog = await orchestrator.fetch_provider_catalog_from_consumer()
    catalog_content = CatalogContent(catalog)
    _logger.info("Found datasets:\n%s", pprint.pformat(list(catalog_content.datasets)))


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv("LOG_LEVEL", "DEBUG"))
    asyncio.run(main())
