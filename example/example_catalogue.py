"""
EDC Catalogue Browsing Example

This example demonstrates how to:
1. Browse the catalogue of assets available from a provider
2. Discover what data is available before initiating transfers
3. Use the ConnectorController to interact with EDC connectors

A catalogue contains metadata about datasets offered by a provider, including
their identifiers, properties, and policies. This is typically the first step
in any data exchange workflow.
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
    """Fetch and display the provider's catalogue of available assets."""

    # Get the provider's protocol URL from environment or use default
    counter_party_protocol_url: str = os.getenv(
        _ENV_COUNTER_PARTY_PROTOCOL_URL, "http://provider.local:9194/protocol"
    )

    # Create controller instance - reads configuration from environment
    controller = ConnectorController()
    _logger.debug("EDC Controller configuration:\n%s", controller.config)

    # Fetch the catalogue from the provider
    # This returns metadata about available datasets, not the actual data
    catalog = await controller.fetch_catalog(
        counter_party_protocol_url=counter_party_protocol_url
    )

    # Display the discovered datasets
    # Each dataset contains information about available assets for transfer
    _logger.info("Found datasets:\n%s", pprint.pformat(list(catalog.datasets)))


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv(_ENV_LOG_LEVEL, "DEBUG"))
    asyncio.run(main())
