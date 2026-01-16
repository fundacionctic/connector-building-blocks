# edcpy

A Python library for interacting with the [Eclipse Dataspace Connector (EDC)](https://github.com/eclipse-edc/Connector).

edcpy is a thin wrapper over the HTTP APIs of an EDC connector. Instead of implementing the flow of HTTP requests yourself, you can leverage edcpy to handle it for you. edcpy uses a RabbitMQ messaging broker as the core infrastructure to decouple and distribute messages from the HTTP consumer backend to consumer applications.

## Installation

```bash
pip install edcpy
```

## Quick Start

### Architecture Overview

edcpy-based applications interact with two main components:

- **EDC Connector**: The core service that serves as a gateway to the data space and implements the Dataspace Protocol.
- **Consumer Backend**: An HTTP API service (included with edcpy) that receives data transfer callbacks and credentials from the EDC Connector. You can start this service using the `run-http-backend` command.

To enable pull transfers, you must configure your EDC Connector to send transfer credentials to the Consumer Backend.

edcpy uses RabbitMQ as the underlying messaging infrastructure for all data transfer operations. Applications can consume messages through two interfaces:

1. **Direct RabbitMQ Access**: Applications connect directly to the RabbitMQ broker using the MessagingClient. Provides full control over message acknowledgment, routing, and queue management.
2. **HTTP Server-Sent Events (SSE)** (Browser-Compatible): Applications consume messages via HTTP streaming endpoints that internally communicate with the RabbitMQ broker. Ideal for browser-based applications or environments where direct AMQP connections are not feasible.

```mermaid
graph TD
    %% External components
    Provider[Provider EDC Connector]
    DataSource[Data Source API]
    
    %% Your edcpy application components
    App[Your Application<br/>using edcpy]
    EDC[Your EDC Connector]
    Backend[Consumer Backend<br/>run-http-backend]
    RabbitMQ[RabbitMQ<br/>Required]
    
    %% Data flows
    App -->|Browse catalog<br/>Negotiate contract<br/>Start transfer| EDC
    EDC <-->|Dataspace Protocol| Provider
    Provider -->|Send credentials| Backend
    Backend -->|Forward messages| RabbitMQ
    RabbitMQ -->|Consume messages| App
    Backend -->|SSE streams<br/>via RabbitMQ| App
    App -->|Use credentials<br/>for HTTP requests| DataSource
    
    %% Styling
    classDef external fill:#e1f5fe
    classDef edcpy fill:#f3e5f5
    classDef required fill:#fff3e0
    
    class Provider,DataSource external
    class App,EDC,Backend edcpy
    class RabbitMQ required
```

### Basic Configuration

Configure edcpy using environment variables:

```bash
# EDC Connector Configuration
export EDC_CONNECTOR_HOST="connector.example.com"
export EDC_CONNECTOR_CONNECTOR_ID="my-connector"
export EDC_CONNECTOR_PARTICIPANT_ID="my-participant"

# Connector API Configuration
export EDC_CONNECTOR_SCHEME="https"                   
export EDC_CONNECTOR_MANAGEMENT_PORT="443"          
export EDC_CONNECTOR_CONTROL_PORT="443"             
export EDC_CONNECTOR_PUBLIC_PORT="443"              
export EDC_CONNECTOR_PROTOCOL_PORT="443"            
export EDC_CONNECTOR_API_KEY="your-secret-api-key"

# Required RabbitMQ broker connection
export EDC_RABBIT_URL="amqp://guest:guest@broker.example.com:5672"
```

### Example 1: Browse Provider Catalog

Discover what data assets are available from a provider:

```python
import asyncio
from edcpy.edc_api import ConnectorController

async def browse_catalog():
    controller = ConnectorController()
    
    # Fetch available datasets from provider
    catalog = await controller.fetch_catalog(
        counter_party_protocol_url="https://connector.provider.com/protocol"
    )
    
    # Convert iterator to list so we can compute its length
    datasets = list(catalog.datasets)
    print(f"Found {len(datasets)} datasets:")

asyncio.run(browse_catalog())
```

### Example 2: HTTP Pull Data Transfer

Request data from a provider and receive credentials to fetch it:

```python
import asyncio
import httpx
from edcpy.edc_api import ConnectorController
from edcpy.messaging import MessagingClient

async def pull_data():
    # Initialize controller and messaging client
    controller = ConnectorController()
    client = MessagingClient("my-consumer-id")
    
    # Start pull consumer to receive credentials
    async with client.pull_consumer() as consumer:
        # Negotiate contract and start transfer
        transfer_details = await controller.run_negotiation_flow(
            counter_party_protocol_url="https://connector.provider.com/protocol",
            counter_party_connector_id="provider-connector",
            asset_query="my-dataset",
            # Optional: increase if the provider paginates the catalog
            catalog_limit=200,
        )
        
        # Request pull credentials
        await controller.run_transfer_flow(
            transfer_details=transfer_details, 
            is_provider_push=False
        )
        
        # Wait for and use credentials to fetch data
        async with consumer.wait_for_message() as pull_message:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.request(**pull_message.request_args)
                data = response.json()
                print(f"Received data: {data}")

asyncio.run(pull_data())
```

### Example 3: HTTP Push Data Transfer

Configure provider to push data to your endpoint:

```python
import asyncio
from edcpy.edc_api import ConnectorController
from edcpy.messaging import MessagingClient

async def receive_push_data():
    controller = ConnectorController()
    client = MessagingClient("my-consumer-id")
    
    # Start push consumer with routing path
    async with client.push_consumer(routing_path="my/routing/path") as consumer:
        # Negotiate contract
        transfer_details = await controller.run_negotiation_flow(
            counter_party_protocol_url="https://connector.provider.com/protocol",
            counter_party_connector_id="provider-connector",
            asset_query="my-dataset"
        )
        
        # Configure push transfer
        await controller.run_transfer_flow(
            transfer_details=transfer_details,
            is_provider_push=True,
            sink_base_url="http://localhost:8000",
            sink_path="/push/my/routing/path",
            sink_method="POST"
        )
        
        # Wait for pushed data
        async with consumer.wait_for_message() as push_message:
            print(f"Received pushed data: {push_message.body}")

asyncio.run(receive_push_data())
```

### Example 4: HTTP Pull using SSE (Browser-Compatible)

Using Server-Sent Events to consume messages from the underlying RabbitMQ broker via HTTP:

```python
import asyncio
import json
import httpx
from edcpy.edc_api import ConnectorController

async def pull_data_with_sse():
    controller = ConnectorController()
    
    # SSE configuration
    consumer_backend_url = "http://localhost:8000"
    api_key = "your-api-key"
    
    # Start SSE stream for provider-based credentials
    sse_url = f"{consumer_backend_url}/pull/stream/provider/provider.example.com"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"}
    
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", sse_url, headers=headers) as response:
            # Negotiate contract and start transfer
            transfer_details = await controller.run_negotiation_flow(
                counter_party_protocol_url="https://provider.example.com/protocol",
                counter_party_connector_id="provider-connector",
                asset_query="my-dataset"
            )
            
            transfer_id = await controller.run_transfer_flow(
                transfer_details=transfer_details, is_provider_push=False
            )
            
            # Listen for credentials via SSE
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    message = json.loads(line[6:])
                    if message.get("transfer_process_id") == transfer_id:
                        # Use credentials to fetch data
                        data_response = await client.request(**message["request_args"])
                        return data_response.json()

asyncio.run(pull_data_with_sse())
```

## Core Components

### EDC API Client

The `ConnectorController` class provides high-level methods for:

- Fetching data catalogs from providers
- Negotiating contracts for data access
- Managing transfer processes
- Creating and managing EDC resources

### Message Consumption Interfaces

edcpy uses RabbitMQ as the core messaging infrastructure. Applications can access messages through two interfaces:

#### 1. Direct RabbitMQ Access (Native Python)

Applications connect directly to the RabbitMQ broker for full control over message handling:

```python
from edcpy.messaging import MessagingClient

# Direct AMQP connection to RabbitMQ broker
client = MessagingClient(consumer_id="my-consumer")

async with client.pull_consumer() as consumer:
    async with consumer.wait_for_message() as pull_message:
        # Process credentials received directly from RabbitMQ
        response = await httpx.get(**pull_message.request_args)
        return response.json()
```

**Benefits**: Full messaging features, message acknowledgment, persistent queues, complex routing patterns.

#### 2. HTTP Server-Sent Events (SSE) Interface

Applications consume the same RabbitMQ messages via HTTP streaming endpoints:

```python
import httpx
import json

# HTTP interface to underlying RabbitMQ messages
headers = {"Authorization": "Bearer your-api-key", "Accept": "text/event-stream"}
url = "http://localhost:8000/pull/stream/provider/provider.example.com"

async with httpx.AsyncClient() as client:
    async with client.stream("GET", url, headers=headers) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                message = json.loads(line[6:])
                # Process credentials served from RabbitMQ via HTTP
                if message.get("type") == "pull_message":
                    data_response = await client.request(**message["request_args"])
                    return data_response.json()
```

**Benefits**: Browser-compatible, HTTP-only connectivity, abstraction from AMQP protocol complexity.

### Consumer Backend

The edcpy library includes an off-the-shelf _Consumer Backend_: an HTTP service that runs alongside your connector to receive pull and push transfer callbacks from counterpart connectors. These callbacks deliver pull access tokens and final responses, respectively:

```bash
run-http-backend
```

The backend provides multiple endpoints and always uses RabbitMQ as the underlying message infrastructure:

- **Transfer Endpoints**: `/pull` and `/push/{routing_path}` for receiving EDC callbacks and forwarding to RabbitMQ
- **SSE Streaming**: `/pull/stream/{transfer_id}` and `/push/stream/{routing_path}` for HTTP access to RabbitMQ messages
- **Message Flow**: All messages are stored in RabbitMQ queues and can be consumed via direct AMQP or HTTP SSE interfaces

The SSE endpoints require authentication via the `Authorization: Bearer {api-key}` header to prevent unauthorized access to transfer credentials.

## Configuration Reference

All configuration is done via environment variables with the `EDC_` prefix. The variables are organized by their function and impact on the system.

### Core Connector Settings (Required)

These fundamental settings define your EDC connector's identity and location. All three are required for basic functionality.

| Variable                       | Description                                                                                                                     | Required | Default |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | -------- | ------- |
| `EDC_CONNECTOR_HOST`           | Hostname or IP address of your EDC connector instance. Used to construct all API URLs.                                          | ✅        | -       |
| `EDC_CONNECTOR_CONNECTOR_ID`   | Unique identifier for your connector instance. Used in dataspace protocol negotiations and must be unique across the dataspace. | ✅        | -       |
| `EDC_CONNECTOR_PARTICIPANT_ID` | Unique identifier for your organization/participant. Used for identity verification and contract negotiations.                  | ✅        | -       |

### Connector API Endpoints (Optional)

These settings control how edcpy connects to your EDC connector's various API endpoints. The library constructs URLs using the pattern: `{scheme}://{host}:{port}{path}`

| Variable                        | Description                                                                                 | Required | Default       |
| ------------------------------- | ------------------------------------------------------------------------------------------- | -------- | ------------- |
| `EDC_CONNECTOR_SCHEME`          | HTTP protocol scheme (http/https) for all connector URLs.                                   | ❌        | `http`        |
| `EDC_CONNECTOR_MANAGEMENT_PORT` | Port for EDC Management API. Used for creating assets, policies, and managing transfers.    | ❌        | `9193`        |
| `EDC_CONNECTOR_MANAGEMENT_PATH` | Base path for Management API endpoints.                                                     | ❌        | `/management` |
| `EDC_CONNECTOR_CONTROL_PORT`    | Port for EDC Control API. Used for internal connector operations and data plane management. | ❌        | `9192`        |
| `EDC_CONNECTOR_CONTROL_PATH`    | Base path for Control API endpoints.                                                        | ❌        | `/control`    |
| `EDC_CONNECTOR_PUBLIC_PORT`     | Port for EDC Public API. Provides read-only access to public connector information.         | ❌        | `9291`        |
| `EDC_CONNECTOR_PUBLIC_PATH`     | Base path for Public API endpoints.                                                         | ❌        | `/public`     |
| `EDC_CONNECTOR_PROTOCOL_PORT`   | Port for EDC Protocol API. Critical for dataspace communication and catalog requests.       | ❌        | `9194`        |
| `EDC_CONNECTOR_PROTOCOL_PATH`   | Base path for Protocol API endpoints. Used in dataspace protocol URLs.                      | ❌        | `/protocol`   |

### Authentication & Security (Optional)

Controls authentication and secure communication with your EDC connector and JWT token validation.

| Variable                       | Description                                                                                           | Required | Default     |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- | -------- | ----------- |
| `EDC_CONNECTOR_API_KEY`        | Authentication token for EDC Management API. Sent in HTTP headers for all management operations.      | ❌        | `None`      |
| `EDC_CONNECTOR_API_KEY_HEADER` | HTTP header name for API key authentication. Must match your EDC connector's configuration.           | ❌        | `X-API-Key` |
| `EDC_CERT_PATH`                | Path to TLS certificate for JWT token validation. Used by the HTTP backend for secure data transfers. | ❌        | `None`      |

### Messaging & Backend (Required)

Controls the RabbitMQ messaging system and HTTP backend service that handle asynchronous data transfer operations.

| Variable            | Description                                                                                                                  | Required | Default |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------- | ------- |
| `EDC_RABBIT_URL`    | RabbitMQ connection URL for messaging. Required for all data transfer operations. Format: `amqp://user:pass@host:port/vhost` | ❌        | `None`  |
| `EDC_HTTP_API_PORT` | Port for the edcpy HTTP backend service. The FastAPI server listens on this port to receive transfer credentials from EDC.   | ❌        | `8000`  |
| `API_AUTH_KEY`      | Authentication key for SSE endpoints. Required when using HTTP SSE interface to access RabbitMQ messages securely.           | ❌        | `None`  |

## License

Licensed under the [EUPL-1.2](https://opensource.org/licenses/EUPL-1.2).
