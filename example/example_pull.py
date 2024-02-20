import asyncio
import logging
import os
import pprint

import coloredlogs

from edcpy.edc_api import ConnectorController

_ENV_LOG_LEVEL = "LOG_LEVEL"
_ENV_COUNTER_PARTY_PROTOCOL_URL = "COUNTER_PARTY_PROTOCOL_URL"
_ENV_COUNTER_PARTY_PARTICIPANT_ID = "COUNTER_PARTY_PARTICIPANT_ID"
_ENV_ASSET_QUERY = "ASSET_QUERY"

_logger = logging.getLogger(__name__)


async def main():
    counter_party_protocol_url: str = os.getenv(
        _ENV_COUNTER_PARTY_PROTOCOL_URL, "http://provider.local:9194/protocol"
    )

    counter_party_participant_id: str = os.getenv(
        _ENV_COUNTER_PARTY_PARTICIPANT_ID, "example-provider"
    )

    asset_query: str = os.getenv(_ENV_ASSET_QUERY, "consumption")

    controller = ConnectorController()
    _logger.debug("Configuration:\n%s", controller.config)

    transfer_process_id = await controller.prepare_to_transfer_asset(
        counter_party_protocol_url=counter_party_protocol_url,
        counter_party_participant_id=counter_party_participant_id,
        asset_query=asset_query,
    )

    _logger.info("Transfer process ID: %s", transfer_process_id)


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv(_ENV_LOG_LEVEL, "DEBUG"))
    asyncio.run(main())
