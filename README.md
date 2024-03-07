# Data Space Connector Building Blocks

- [Data Space Connector Building Blocks](#data-space-connector-building-blocks)
  - [Introduction](#introduction)
  - [Public Artifacts](#public-artifacts)
    - [Configuration of the Connector Image](#configuration-of-the-connector-image)
  - [Example](#example)
    - [Configuration and Deployment](#configuration-and-deployment)
      - [Provider](#provider)
      - [Consumer](#consumer)
    - [Consumer Pull](#consumer-pull)
    - [Provider Push](#provider-push)
  - [Frequently Asked Questions](#frequently-asked-questions)

> [!CAUTION]
> Please note that most of the code in this repository is still a work in progress and will thus likely go through several breaking changes throughout its development.

## Introduction

This repository contains a collection of software components that aim at simplifying the deployment of data space connectors based on the [Eclipse Dataspace Components](https://eclipse-edc.github.io/docs/#/) (EDC) ecosystem and the interactions of applications with those connectors. Specifically, the following components are provided here:

* An EDC connector extension capable of interpreting an OpenAPI schema and generating a set of assets within the data space to represent the services provided by a participant component. The underlying idea is to enable participants to develop their own HTTP APIs while the extension abstracts away the intricacies of exposing these HTTP APIs to the data space.
* An EDC connector extension that implements authentication via W3C Verifiable Credentials.
* A Python library that implements the logic to interact with the [Management](https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api) and [Control](https://app.swaggerhub.com/apis/eclipse-edc-bot/control-api) APIs of the EDC connector to go through the necessary steps to transfer data between two participants in the data space.

The repository is organized as follows:

* The `connector` folder contains a Java project with a very early draft version of the connector extensions and a connector launcher.
* The `mock-backend` folder contains an example HTTP API as exposed by a data space participant. This API is described by an [OpenAPI](https://learn.openapis.org/) document. The logic of the component itself does not hold any value; its purpose is to demonstrate where each participant should contribute.
* The `edcpy` folder contains a Python package built on top of Poetry, providing a series of utilities to interact with a data space based on the EDC ecosystem. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process. Additionally, it offers an example implementation of a _consumer backend_.
* The `dev-config` and `example` folders, alongside the `Vagrantfile`, contain the configuration and scripts necessary to deploy a consumer and a provider, and to demonstrate end-to-end communications based on the Dataspace Protocol between them.

## Public Artifacts

This repository publishes two software artifacts for convenience:

* The `edcpy` Python package, which is [published to PyPI](https://pypi.org/project/edcpy/).
* The `agmangas/edc-connector` Docker image for the connector launcher, which is [published to Docker Hub](https://hub.docker.com/r/agmangas/edc-connector).

### Configuration of the Connector Image

Although the later examples go into more detail about how to configure the connector, it is relevant to note that the `agmangas/edc-connector` image expects the following environment variables:

| Variable Name          | Description                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `PROPERTIES_FILE_PATH` | Path to a properties file containing the configuration for the connector.                                                      |
| `KEYSTORE_PATH`        | Path to a keystore file containing the private key and certificate for the connector. The keystore should be in PKCS12 format. |
| `KEYSTORE_PASSWORD`    | The password for the keystore.                                                                                                 |

## Example

The example in this section will illustrate the following scenario:

* There is a data space participant with an HTTP API (i.e., the [Mock HTTP API](mock-backend)) that needs to be exposed to the data space. This participant is the **provider**.
* There is another data space participant that wants to consume the data from the HTTP API of the first participant. This participant is the **consumer**.
* Both the provider and the consumer start from scratch regarding the configuration of the connector and the deployment of the necessary components.
* Both the provider and the consumer have installed the following prerequisites:
  * [Docker](https://www.docker.com/products/docker-desktop/): All services, including the connector, will be deployed as Docker containers.
  * [Taskfile](https://taskfile.dev/): We'll use Taskfile as a task runner in this example to simplify the deployment process and ensure its reproducibility.
  * Python and [Poetry](https://python-poetry.org/): To run the example scripts.
* To simplify the example, no authentication will be used. Nevertheless, it's worth noting that the connector will eventually support authentication via W3C Verifiable Credentials (VC) for real-world scenarios.

> [!NOTE]
> This example assumes that all tasks are executed on the same machine.

> [!TIP]
> You can review the details of what is exactly executed by each task in the [Taskfile](Taskfile.yml).

### Configuration and Deployment

#### Provider

First, we will deploy the services of the provider participant.

**1. Deploy the [Mock HTTP API](mock-backend)**

This HTTP API is the component that encapsulates the value contributed by the provider to the data space. The services and datasets offered by the provider to other participants are accessed via this HTTP API. In this example, we refer to this component as the _Mock HTTP API_.

The Mock HTTP API is not exposed to the Internet; it is only accessible by the connector. The connector acts as a gateway, exposing the API to the data space in a secure and controlled manner.

To start the Mock HTTP API, run the following command:

```console
task up-provider-mock-api
```

This command will start the Mock HTTP API as a Docker container. It will be accessible by default at port 9090:

```console
$ docker ps
CONTAINER ID   IMAGE                   COMMAND                  CREATED              STATUS              PORTS                    NAMES
01665cb4bf43   mock-backend-http_api   "uvicorn http-api:ap…"   About a minute ago   Up About a minute   0.0.0.0:9090->9090/tcp   mock_backend_http_api
```

If you visit the documentation at [http://localhost:9090/docs](http://localhost:9090/docs), you'll find that the Mock HTTP API exposes a couple of endpoints: one for executing an electricity consumption prediction model and another for retrieving electricity consumption data. These endpoints serve as mocks and return dummy data. The documentation is automatically generated from the OpenAPI schema file that describes the API.

**2. Generate a keystore containing the private key and certificate**

> [!WARNING]
> We should eventually stop using keystores, as they have been marked as unsafe by the original authors of the connector.

The connector requires a password-protected keystore in PKCS12 format (`.pfx`) containing its private key and certificate.

In this example, we will generate the certificate and key manually. However, in a real-world scenario, the keystore could be dynamically created by reading the connector's wallet during connector initialization.

To generate the keystore, run the following command:

```console
task create-example-certs-provider
```

This will [build a Docker image](scripts/Dockerfile) with the dependencies for the keystore generation script ([`create-certs.sh`](scripts/create-certs.sh)) and run a container that executes that script. The keystore will be saved in the `dev-config/certs-provider` directory:

```console
$ ls -lah dev-config/certs-provider/
total 40
drwxr-xr-x   6 agmangas  staff   192B Mar  7 14:19 .
drwxr-xr-x  14 agmangas  staff   448B Mar  7 14:19 ..
-rw-r--r--   1 agmangas  staff   2.0K Mar  7 14:19 cert.pem
-rw-------   1 agmangas  staff   4.2K Mar  7 14:19 cert.pfx
-rw-------   1 agmangas  staff   3.2K Mar  7 14:19 key.pem
-rw-r--r--   1 agmangas  staff   2.1K Mar  7 14:19 vault.properties
```

You can modify the keystore password and the output directory by editing the variables in the [Taskfile](Taskfile.yml).

**3. Prepare the configuration properties file**

All the configuration details for the connector are defined in a properties file, which is passed as an argument to the connector JAR.

The properties file for the provider is located at [`dev-config/dev-provider.properties`](dev-config/dev-provider.properties). We'll go through all the properties in the following paragraphs.

```properties
edc.participant.id=example-provider
edc.ids.id=example-provider
```

These properties are the connector ID that uniquely identify each participant in the data space. Experience has shown that using the same value for both properties is preferable to avoid confusion.

```properties
edc.hostname=host.docker.internal
```

This should be the public hostname where the connector is deployed. Please note that it should be the name of the host machine, rather than the container's hostname.

> [!NOTE]
> You will notice that the properties file uses the [`host.docker.internal` hostname](https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host). This hostname is special as it resolves to the host machine from within a Docker container.

```properties
web.http.port=19191
web.http.path=/api
web.http.management.port=19193
web.http.management.path=/management
web.http.protocol.port=19194
web.http.protocol.path=/protocol
web.http.public.port=19291
web.http.public.path=/public
web.http.control.port=19192
web.http.control.path=/control
```

The ports and paths where the various interfaces of the connector are available. These interfaces include the Management, Protocol, Public and Control APIs.

> [!NOTE]
> The provider ports are configured to be `19xxx`, while the consumer ports are `29xxx`.

```properties
edc.dsp.callback.address=http://host.docker.internal:19194/protocol
```

This is the public Dataspace Protocol URL that other connectors will use to communicate with our connector. It should be based on the `edc.hostname`, `web.http.protocol.port` and `web.http.protocol.path` properties.

```properties
edc.receiver.http.endpoint=http://host.docker.internal:18000/pull
```

This is the URL where the consumer backend will be listening in the Consumer Pull use case. Since a connector strictly acting as a provider does not require a consumer backend service, this property is not relevant for the provider.

```properties
edc.dataplane.token.validation.endpoint=http://host.docker.internal:19192/control/token
```

Please check the [Data Plane API extension](https://github.com/eclipse-edc/Connector/blob/v0.5.1/extensions/data-plane/data-plane-control-api/README.md) for information regarding this property.

```properties
edc.public.key.alias=publickey
edc.transfer.dataplane.token.signer.privatekey.alias=datacellar
edc.transfer.proxy.token.signer.privatekey.alias=datacellar
edc.transfer.proxy.token.verifier.publickey.alias=publickey
```

These are the aliases for the private key and public certificate. The value `publickey` refers to the item containing the public certificate in the `vault.properties` file.

```properties
eu.datacellar.openapi.url=http://host.docker.internal:9090/openapi.json
```

> [!NOTE]
> All properties with names starting with `eu.datacellar` are defined within the extensions contained in this repository and are not part of the original connector codebase.

This is the URL where the OpenAPI schema file of the Mock HTTP API is accessible. The connector will retrieve this file to dynamically build the assets and expose them to the data space.

Finally, the `eu.datacellar.wallet.*`, `eu.datacellar.trust.*` and `eu.datacellar.uniresolver.*` properties are part of the W3C Verifiable Credentials extension and are not relevant for this example either.

**4. Deploy the connector**

You need to deploy the stack defined in `docker-compose-provider.yml` to start the provider connector:

```console
docker compose -f ./docker-compose-provider.yml up -d --build --wait
```

This command will build the image defined in the [`Dockerfile`](Dockerfile) and run a container using the properties file and keystore that we prepared earlier.

Once the provider connector is running, you can check its status by running the following command:

```console
$ docker ps -a --filter name="provider.*"
CONTAINER ID   IMAGE          COMMAND                  CREATED          STATUS          PORTS                                                            NAMES
2fb81b1dc25b   671518adc863   "/bin/sh -c '${PATH_…"   16 minutes ago   Up 16 minutes   0.0.0.0:19191-19194->19191-19194/tcp, 0.0.0.0:19291->19291/tcp   provider
```

#### Consumer

After deploying the provider, we can proceed with deploying the consumer's services.

**1. Generate a keystore containing the private key and certificate**

This step is equivalent to the one we performed for the provider. The only difference is that the keystore will be saved in the `dev-config/certs-consumer` directory:

```console
task create-example-certs-consumer
```

**2. Prepare the configuration properties file**

The properties file for the consumer is located at [`dev-config/dev-consumer.properties`](dev-config/dev-consumer.properties).

The properties are similar to the ones used for the provider, with the exception that, in the case of the consumer, the `edc.receiver.http.endpoint` property must point to the Consumer Pull URL of the consumer backend service (see the `consumer_backend` service in the [`docker-compose-consumer.yml`](docker-compose-consumer.yml) file):

```properties
edc.receiver.http.endpoint=http://host.docker.internal:28000/pull
```

**3. Deploy the connector alongside the consumer backend and the message broker**

> [!TIP]
> Check the [FAQs](#frequently-asked-questions) to see why a **message broker** is necessary and what a **consumer backend** is.

You need to deploy the stack defined in `docker-compose-consumer.yml` to start the consumer connector, the consumer backend and the message broker:

```console
docker compose -f ./docker-compose-consumer.yml up -d --build --wait
```

The connector image is the same as the one used for the provider, so the build should be much faster this time.

Once the consumer services are running, you can check their status by running the following command:

```console
$ docker ps -a --filter name="consumer.*"
CONTAINER ID   IMAGE                      COMMAND                  CREATED         STATUS         PORTS                                                                                                         NAMES
2db8c161dcb6   edc-connector              "/bin/sh -c '${PATH_…"   5 minutes ago   Up 5 minutes   0.0.0.0:29191-29194->29191-29194/tcp, 0.0.0.0:29291->29291/tcp                                                consumer
23c40c1a3675   edc-connector              "run-http-backend"       5 minutes ago   Up 5 minutes   0.0.0.0:28000->28000/tcp                                                                                      consumer_backend
5530123dbee6   rabbitmq:3.11-management   "docker-entrypoint.s…"   5 minutes ago   Up 5 minutes   4369/tcp, 5671/tcp, 0.0.0.0:5672->5672/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 0.0.0.0:15672->15672/tcp   consumer_broker
```

### Consumer Pull

This example demonstrates the **Consumer Pull** type of data transfer as defined in the [Transfer Data Plane](https://github.com/eclipse-edc/Connector/tree/v0.5.1/extensions/control-plane/transfer/transfer-data-plane) extension.

In this case, the consumer _pulls_ data from the provider by sending HTTP requests to the provider’s data plane public API. The provider proxies these requests to the Mock HTTP API. A single access token can be reused to send multiple requests to the same HTTP endpoint with different body contents and query arguments.

The diagram below presents an overview of this data transfer process as implemented in this example:

![Consumer Pull diagram](diagrams/http-pull-example.png)

It is interesting to note that when the consumer application sends a request to the HTTP API through the provider connector, the provider connector acts as a proxy (step 6 in the diagram). This means that the HTTP API is not directly exposed to the Internet, and its access is controlled by the provider connector, even if the HTTP API itself does not implement any authentication mechanism.

The example is implemented in the [`example_pull.py`](example/example_pull.py) script.

The following list presents some key points about the script to help you understand what it does and how it works:

* The script uses the `edcpy` package to interact with the connector. This is just a convenience, and you can implement the same logic using any programming language. In other words, `edcpy` is not a requirement to interact with the connector; it's just a tool to make the process easier.
* The `edcpy` package basically implements the logic described in the [transfer samples of the eclipse-edc/Samples](https://github.com/eclipse-edc/Samples/tree/main/transfer) repository. Instead of having to manually execute the HTTP requests, the package encapsulates this logic in a more developer-friendly way.
* The `ConnectorController` is the main entry point in `edcpy` to interact with the connector. Instances of this class can be configured via environment variables that have the prefix `EDC_` or directly through the constructor. See the [`edcpy/config.py`](edcpy/edcpy/config.py) file for more details on the available configuration options.
* The script itself is also configured via environment variables (check the `AppConfig` class).
* The script utilises an `asyncio.Queue` to asynchronously buffer messages from the message broker. Using a queue is not mandatory, you can implement the same logic using any other mechanism. The details of dealing with the message broker are abstracted by the `with_messaging_app` context manager.
* To consume an asset from a connector, you need to know the asset ID (e.g. `GET-consumption`). In this example, the asset ID is hardcoded in the script, but in a real-world scenario, it could be dynamically retrieved from the catalogue of the connector.

> [!TIP]
> We highly recommend you to check the [transfer samples in eclipse-edc/Samples](https://github.com/eclipse-edc/Samples/tree/main/transfer) to better understand what the script is doing.

To run the script, the first thing we need to do is ensure that the appropriate environment variables are set. You can export the variables to your shell by running the following command:

```console
export $(grep -v '^#' ./dev-config/.env.dev.consumer | xargs)
```

You can check that the variables were correctly set:

```console
$ env | grep EDC
EDC_CONNECTOR_HOST=host.docker.internal
EDC_CONNECTOR_CONNECTOR_ID=example-consumer
EDC_CONNECTOR_PARTICIPANT_ID=example-consumer
EDC_CONNECTOR_MANAGEMENT_PORT=29193
EDC_CONNECTOR_CONTROL_PORT=29192
EDC_CONNECTOR_PUBLIC_PORT=29291
EDC_CONNECTOR_PROTOCOL_PORT=29194
EDC_RABBIT_URL=amqp://guest:guest@localhost:5672
```

Then, ensure that the dependencies of the `edcpy` package are installed. A Python virtualenv will be created in `.venv`:

```console
$ cd edcpy
$ poetry install

[...]

  • Installing environ-config (23.2.0)
  • Installing fastapi (0.109.2)
  • Installing faststream (0.4.3)
  • Installing pyjwt (2.8.0)
  • Installing pytest (7.4.4)
  • Installing python-slugify (8.0.4)
  • Installing requests (2.31.0)

Installing the current project: edcpy (0.2.0a0)
```

Finally, you can run the example script:

```console
$ poetry run python ../example/example_pull.py

[...]

2024-03-07 18:37:51 agmangas-macpro-m1.local __main__[44749] INFO Sending HTTP POST request with arguments:
{'headers': {'Authorization': 'eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3MDk4MzM2NzEsImRhZCI6IntcInByb3BlcnRpZXNcIjp7XCJwYXRoXCI6XCIvY29uc3VtcHRpb24vcHJlZGljdGlvblwiLFwibWV0aG9kXCI6XCJQT1NUXCIsXCJodHRwczovL3czaWQub3JnL2VkYy92MC4wLjEvbnMvdHlwZVwiOlwiSHR0cERhdGFcIixcInByb3h5UXVlcnlQYXJhbXNcIjpcInRydWVcIixcIm5hbWVcIjpcImRhdGEtYWRkcmVzcy1QT1NULWNvbnN1bXB0aW9uLXByZWRpY3Rpb25cIixcInByb3h5Qm9keVwiOlwidHJ1ZVwiLFwiY29udGVudFR5cGVcIjpcImFwcGxpY2F0aW9uL2pzb25cIixcImh0dHBzOi8vdzNpZC5vcmcvZWRjL3YwLjAuMS9ucy9iYXNlVXJsXCI6XCJodHRwOi8vaG9zdC5kb2NrZXIuaW50ZXJuYWw6OTA5MFwifX0ifQ.Yj1JPPHjc3ELFvIb_V95hFGDEuPt1S0Or7Lgmu7LFxgkQGsNYRq6W45Jt2TAILGrCv34L1g8DQiB5NT3hhnnGHXn9O95-PKyWlzDLFpf4iFQzwkXJJbTA7kDCrGiyqTmgZMfI3U-CDcO_BuTuBk-G6I5fJE15elnyNRhXK7feOTrzwrz0Cz2Xdzj0cUn_MCDfeSMFWFzatDJm-2nRCElEnqpr3ouFVw-Xhq0XAAEB8nF4-0BM-HzBfQ5V8qLp8rxE_ExzkJaDmUAsVRSvJv9C1nnfIkkWn8geYV0-SxRkHx8mTjQLl9jAL3Nq_pBT8rrrtV7b8dYX42McMKDS7YPKdyqFss8jm4dUO2CWEfbEhOoapT0qN93l3W-OLwuthJxoaq4tpSQ3zsHHPZuaOS-HdcU45x_0vS1zGzPhII1chDPi3nH18_7ebu4FDG6smbB3ew1k4Kv0AH09wLNNUzqaXwhbb0ajBd-QNT3M3cTDSVBWlpgP07OTzWYVnXvJqQRbSXqlX30mjyYv19L6TtDJCtw9DIMKftURPHrmqDh4QKExrafZmUQcUfABfakmcHGB2XW5L-Yv6ba9bHMYkDAVE5SXme4gzcJXwfM3e4wm9XyBwu3sPzjlocAPpmhqBij8zhLRilIHbuSJqq8tuJqffmjO94GhCgwSSSzgYieaJg'},
 'json': {'date_from': '2023-06-15T14:30:00',
          'date_to': '2023-06-15T18:00:00',
          'location': 'Asturias'},
 'method': 'POST',
 'url': 'http://host.docker.internal:19291/public/'}

2024-03-07 18:37:51 agmangas-macpro-m1.local httpx[44749] INFO HTTP Request: POST http://host.docker.internal:19291/public/ "HTTP/1.1 200 OK"

2024-03-07 18:37:51 agmangas-macpro-m1.local __main__[44749] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2023-06-15T14:30:00+00:00', 'value': 82},
             {'date': '2023-06-15T15:30:00+00:00', 'value': 82},
             {'date': '2023-06-15T16:30:00+00:00', 'value': 97},
             {'date': '2023-06-15T17:30:00+00:00', 'value': 88}]}

[...]
```

### Provider Push

This example demonstrates the **Provider Push** data transfer type, which is the alternative to the aforementioned Consumer Pull type.

In this case, the provider pushes data to the consumer by sending HTTP requests to the consumer's backend directly. These requests contain the responses from the Mock HTTP API.

![Provider Push diagram](diagrams/http-push-example.png)

If you have already set the environment variables for the consumer and installed the dependencies for the `edcpy` package, you can run the example script:

```console
$ poetry run python ../example/example_push.py

[...]

2024-03-07 20:42:12 agmangas-macpro-m1.local __main__[57376] INFO Received response from Mock Backend HTTP API:
{'location': 'Asturias',
 'results': [{'date': '2024-03-06T00:00:00+00:00', 'value': 72},
             {'date': '2024-03-06T01:00:00+00:00', 'value': 39},
             {'date': '2024-03-06T02:00:00+00:00', 'value': 52},
             {'date': '2024-03-06T03:00:00+00:00', 'value': 36},
             {'date': '2024-03-06T04:00:00+00:00', 'value': 53},
             {'date': '2024-03-06T05:00:00+00:00', 'value': 82},
             {'date': '2024-03-06T06:00:00+00:00', 'value': 86},
             {'date': '2024-03-06T07:00:00+00:00', 'value': 39},
             {'date': '2024-03-06T08:00:00+00:00', 'value': 19},
             {'date': '2024-03-06T09:00:00+00:00', 'value': 61},
             {'date': '2024-03-06T10:00:00+00:00', 'value': 30},
             {'date': '2024-03-06T11:00:00+00:00', 'value': 99},
             {'date': '2024-03-06T12:00:00+00:00', 'value': 18},
             {'date': '2024-03-06T13:00:00+00:00', 'value': 0},
             {'date': '2024-03-06T14:00:00+00:00', 'value': 76},
             {'date': '2024-03-06T15:00:00+00:00', 'value': 91},
             {'date': '2024-03-06T16:00:00+00:00', 'value': 6},
             {'date': '2024-03-06T17:00:00+00:00', 'value': 72},
             {'date': '2024-03-06T18:00:00+00:00', 'value': 55},
             {'date': '2024-03-06T19:00:00+00:00', 'value': 64},
             {'date': '2024-03-06T20:00:00+00:00', 'value': 7},
             {'date': '2024-03-06T21:00:00+00:00', 'value': 35},
             {'date': '2024-03-06T22:00:00+00:00', 'value': 22},
             {'date': '2024-03-06T23:00:00+00:00', 'value': 29}]}
```

## Frequently Asked Questions

**What exactly is a _consumer backend_?**

A **consumer backend** is a service within the connector ecosystem with two primary responsibilities:

* In the [Consumer Pull](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane#consumer-pull) use case, it receives the `EndpointDataReference` object from the provider side. This object contains details on how and where to send the HTTP request to obtain the final response.
* In the [Provider Push](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane#provider-push) use case, it receives the actual final response.

The **consumer backend** implementation is provided out-of-the-box by the [`edcpy`](edcpy) package. It is not necessary for each participant to develop its own version; the same implementation can be reused across the data space.

**How does the provider know how to expose the Mock Backend HTTP API and create the related assets in the data space?**

The Mock Backend HTTP API must expose a schema file that adheres to the [OpenAPI specifications](https://spec.openapis.org/oas/latest.html). The URL to this file is provided as a configuration property (`eu.datacellar.openapi.url`) to the provider. Upon initialization, the provider retrieves the schema file and builds the necessary assets.

The JSON file of the API schema serves as the authoritative source, determining how the HTTP API will be represented within the data space.

**What is the role of the RabbitMQ message broker?**

In both the _Consumer Pull_ and _Provider Push_ approaches, an HTTP server (i.e. _consumer backend_) needs to be running on the consumer's side.

In this project, [RabbitMQ](https://www.rabbitmq.com/) was chosen as a tool to decouple the messages received by the _consumer backend_ and enable arbitrary applications to subscribe to and process them asynchronously.

RabbitMQ was selected due to its popularity and ease of use as a message broker. Other options, such as Redis, could have been chosen as well. It's worth noting that a message broker is not strictly necessary. Any mechanism capable of passing the messages received on the _consumer backend_ to the application would be suitable.

**What is the `edcpy` package, and is Python required?**

The [Management](https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api) and [Control](https://app.swaggerhub.com/apis/eclipse-edc-bot/control-api) APIs of the Eclipse Connector involve complex interactions with multiple requests. The `edcpy` package serves as a means to encapsulate this logic, making it reusable. Additionally, it provides a ready-to-use _consumer backend_ that integrates with RabbitMQ.

However, it's important to note that the use of Python is not mandatory. The `edcpy` package is designed to (hopefully) facilitate the development process, but if you prefer to use another programming language, you have the flexibility to build your own _consumer backend_ and directly communicate with the Management API.

**What are the minimum requirements that an HTTP API must have to be interoperable with the _Core Connector_?**

We will strive to ensure that the core connector is compatible with any arbitrary HTTP API, as long as it is properly described using the OpenAPI specification.

This means that you should have the liberty of using whatever technology stack you feel more comfortable with to develop the API.

**Are OpenAPI-based APIs the only supported data sources?**

Yes, for the time being. The _Core Connector_ is still in its early stages of development, and we are focusing on the most common use cases. However, we are open to expanding the scope of the project in the future.

In any case, the OpenAPI specification is flexible enough to describe a wide variety of APIs. It should be fairly simple to expose your existing data source as an OpenAPI-based API.