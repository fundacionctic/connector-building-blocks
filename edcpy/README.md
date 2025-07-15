# edcpy

A Python library for interacting with the [Eclipse Dataspace Connector (EDC)](https://github.com/eclipse-edc/Connector).

edcpy is a thin wrapper over the HTTP APIs of an EDC connector. Instead of implementing the flow of HTTP requests yourself, you can leverage edcpy to handle it for you. Note that edcpy makes a specific design choice: to decouple messages received by the HTTP server consumer backend, it introduces a RabbitMQ messaging broker as the main broker to distribute messages to consumer applications.

## Installation

```bash
pip install edcpy
```

## Quick Start

### Basic Configuration

Set environment variables for your EDC connector:

```bash
export EDC_CONNECTOR_HOST="localhost"
export EDC_CONNECTOR_CONNECTOR_ID="my-connector"
export EDC_CONNECTOR_PARTICIPANT_ID="my-participant"
```

### Contract Negotiation and Data Transfer

```python
import asyncio
from edcpy.edc_api import ConnectorController

async def main():
    # Initialize controller
    controller = ConnectorController()
    
    # Negotiate contract and start transfer
    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url="http://provider:9194/protocol",
        counter_party_connector_id="provider-connector",
        asset_query="my-dataset"
    )
    
    print(f"Transfer ID: {transfer_details.transfer_process_id}")

asyncio.run(main())
```

### Asset Management

```python
from edcpy.edc_api import create_asset
from edcpy.models.asset import Asset

# Create an HTTP data asset
asset_data = Asset.build_http_data(
    source_base_url="https://api.example.com/data",
    source_method="GET",
    source_content_type="application/json"
)

# Register with EDC
await create_asset(
    management_url="http://localhost:9193/management",
    asset_data=asset_data
)
```

## Core Components

### EDC API Client

The `ConnectorController` class provides high-level methods for:

- Fetching data catalogs from providers
- Negotiating contracts for data access
- Managing transfer processes
- Creating and managing EDC resources

### Messaging System

This library integrates RabbitMQ to support asynchronous messaging in data space environments. This approach decouples the HTTP server consumer backend from the consumer applications: the consumer applications connect to the RabbitMQ broker to listen for the results of their consumer pull and provider push data transfers:

```python
from edcpy.messaging import MessagingClient

async def handle_pull_message(message):
    # Process HTTP pull transfer credentials
    response = await httpx.get(**message.request_args)
    return response.json()

# Set up message consumer
client = MessagingClient(consumer_id="my-consumer")
await client.consume_http_pull_queue(
    provider_host="provider.example.com",
    handler=handle_pull_message
)
```

### HTTP Backend

Run a FastAPI server to receive transfer credentials:

```bash
run-http-backend
```

The server exposes endpoints for EDC to deliver transfer credentials, which are then forwarded to your messaging queues.

## Configuration

Configure via environment variables with the `EDC_` prefix:

| Variable                        | Description              | Default  |
| ------------------------------- | ------------------------ | -------- |
| `EDC_CONNECTOR_HOST`            | EDC connector hostname   | Required |
| `EDC_CONNECTOR_CONNECTOR_ID`    | Connector identifier     | Required |
| `EDC_CONNECTOR_PARTICIPANT_ID`  | Participant identifier   | Required |
| `EDC_CONNECTOR_MANAGEMENT_PORT` | Management API port      | 9193     |
| `EDC_CONNECTOR_PROTOCOL_PORT`   | Protocol endpoint port   | 9194     |
| `EDC_CONNECTOR_API_KEY`         | API authentication key   | None     |
| `EDC_RABBIT_URL`                | RabbitMQ connection URL  | None     |
| `EDC_CERT_PATH`                 | Path to certificate file | None     |

## Models

The library includes Pydantic models for EDC entities:

- `Asset`: Data assets with HTTP endpoints
- `ContractDefinition`: Contract templates
- `PolicyDefinition`: Access policies
- `ContractNegotiation`: Contract negotiation requests
- `TransferProcess`: Data transfer processes
- `DataPlaneInstance`: Data plane configurations

## License

Licensed under the [EUPL-1.2](https://opensource.org/licenses/EUPL-1.2).

