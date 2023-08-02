# Eclipse Dataspace Components Proof of Concept

- [Eclipse Dataspace Components Proof of Concept](#eclipse-dataspace-components-proof-of-concept)
  - [Future Work](#future-work)
  - [Introduction](#introduction)
  - [Public Artifacts](#public-artifacts)
    - [Configuration of the Connector Image](#configuration-of-the-connector-image)
  - [About Keycloak and OAuth 2](#about-keycloak-and-oauth-2)
  - [Examples](#examples)
    - [Prerequisites](#prerequisites)
    - [Consumer Pull](#consumer-pull)
    - [Provider Push](#provider-push)
  - [Frequently Asked Questions](#frequently-asked-questions)

## Future Work

- [ ] Update README to show a comparative between a non-IDS data exchange and an IDS-based data exchange.
- [ ] Integrate Gaia-X Self-Descriptions, the [Gaia-X Federated Catalogue](https://gitlab.eclipse.org/eclipse/xfsc/cat/fc-service) and the [Gaia-X Compliance Service](https://gitlab.com/gaia-x/lab/compliance/gx-compliance).
- [ ] Replace Keycloak by DAPS as the identity service.

## Introduction

This project contains a proof of concept that aims to automate the deployment of a Minimum Viable Dataspace and demonstrate how arbitrary data sources can be integrated into the data space using the Eclipse Dataspace Components software stack.

The approach taken here is that **any data space participant component can expose an HTTP API described by a standard OpenAPI schema**. Then, there is a Core Connector that is able to understand this schema and create a series of assets in the data space to represent the HTTP endpoints. These endpoints, in turn, provide access to the datasets and services offered by the participant component in question.

The repository is organized as follows:

* The `connector` folder contains a Java project with a very early draft version of the _Core Connector_ extension. This extension is responsible for creating the assets in the data space based on the OpenAPI schema of the participant component.
* The `mock-component` folder contains an example data space participant that exposes both an HTTP API and an event-driven API based on RabbitMQ. These APIs are described by [OpenAPI](https://learn.openapis.org/) and [AsyncAPI](https://www.asyncapi.com/docs) documents, respectively. The logic of the component itself does not hold any value; its purpose is to demonstrate where each partner should contribute.

> Support for AsyncAPI and event-driven APIs is a nice-to-have that is not currently being prioritized. It will be addressed at a later stage if time permits and there are no technological roadblocks.

* The `edcpy` folder contains a Python package built on top of [Poetry](https://python-poetry.org/), providing a series of utilities to interact with an EDC-based dataspace. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a [Transfer Process](https://eclipse-edc.github.io/docs/#/submodule/Connector/docs/developer/architecture/domain-model?id=transfer-process). Additionally, it offers an example implementation of a [Consumer Backend](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).
* The `example` folder contains the configuration files required for the end-to-end example of an interaction between a provider and consumer. This example is one of the main contributions of this repository and aims to clarify any doubts regarding how to integrate a regular service or API into a data space.

## Public Artifacts

This repository publishes two software artifacts for convenience:

* The `edcpy` Python package, which is [published to PyPI](https://pypi.org/project/edcpy/).
* The `agmangas/edc-connector` Docker image for the _Core Connector_, which is [published to Docker Hub](https://hub.docker.com/r/agmangas/edc-connector).

### Configuration of the Connector Image 

Although the later examples go into more detail about how to configure the connector, it is relevant to note that the `agmangas/edc-connector` image expects the following environment variables:

| Variable Name          | Description                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `PROPERTIES_FILE_PATH` | Path to a properties file containing the configuration for the connector.                                                      |
| `KEYSTORE_PATH`        | Path to a keystore file containing the private key and certificate for the connector. The keystore should be in PKCS12 format. |
| `KEYSTORE_PASSWORD`    | The password for the keystore.                                                                                                 |

## About Keycloak and OAuth 2

The Gradle project of the _Core Connector_ defines a property named `useOauthIdentity` that can be used to enable or disable support for identity based on OAuth 2. Specifically, this property is checked to determine whether the [OAuth 2 Identity Service](https://github.com/eclipse-edc/Connector/tree/main/extensions/common/iam/oauth2/oauth2-core) needs to be included in the project dependencies.

When `useOauthIdentity=true`, the connector instances will communicate with a Keycloak server to retrieve access tokens and validate them. These tokens are then used to authenticate the requests sent to the data space.

> We use Keycloak instead of **DAPS** due to the maturity of Keycloak and to reduce the complexity of the setup. Using DAPS would provide a more interoperable scenario; however, we are currently not focusing on that aspect.

A connector instance is represented in Keycloak as a _Client_. These _Clients_ need to be configured in a particular way to ensure that the connector can successfully authenticate with Keycloak. The `edcpy` package [provides a command line utility](edcpy/edcpy/keycloak.py) to automate this configuration process.

## Examples

There is a `Vagrantfile` in the root of the repository, which serves as the configuration file for Vagrant. [Vagrant](https://www.vagrantup.com/) is a tool utilized here to generate reproducible versions of two separate Ubuntu Virtual Machines: one for the provider and another for the consumer. This approach guarantees that the examples portray a more realistic scenario where the consumer and provider are deployed on different instances. Consequently, this distinction is reflected in the configuration files, providing a more illustrative demonstration rather than relying only on localhost access for all configuration properties.

After installing Vagrant on your system, simply run `vagrant up` to create both the provider and the consumer. The `Vagrantfile` is configured to handle all the necessary provisioning steps, such as installing dependencies and building the connector. Once the build process is complete, you can log into the consumer and provider by using `vagrant ssh consumer` or `vagrant ssh provider`.

The provisioning scripts build the Docker images locally. However, there are also two alternative Compose files ending in `-hub-image.yml` that show how to use the public images instead.

We use Multicast DNS to ensure that `provider.local` resolves to the provider’s IP and that `consumer.local` resolves to the consumers’ IP. This forces us to install `avahi-daemon` and `libnss-mdns` in both the consumer and provider, and also to bind the volumes `/var/run/dbus` and `/var/run/avahi-daemon/socket` on all Docker containers.

The following examples demonstrate two distinct approaches, which are summarized in the table below for clarity:

| Approach          | Key Characteristics                                                                                                                                              |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Provider Push** | The provider pushes data to the consumer by sending HTTP requests to the consumer's backend directly. These requests contain the responses from the mock API.    |
| **Consumer Pull** | The consumer pulls data from the provider by sending HTTP requests to the provider’s data plane public API. The provider proxies these requests to the mock API. |

> Please note that the examples below are run in the Consumer VM, which can be accessed by running `vagrant ssh consumer`.

### Prerequisites

* [VirtualBox](https://www.virtualbox.org/wiki/Downloads): a popular virtualization product.
* [Vagrant](https://developer.hashicorp.com/vagrant/downloads): a command line tool for managing virtual machines.

You just need to download and install the releases for your operating system. Vagrant should be able to find and use the [VirtualBox provider](https://developer.hashicorp.com/vagrant/docs/providers/virtualbox) automatically.

There are no other prerequisites, as Vagrant will take care of installing all the necessary dependencies inside the virtual machines.

### Consumer Pull

This example demonstrates the _Consumer Pull_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

This approach tends to be more efficient than the _Provider Push_ approach, as a single access token can be reused to send multiple requests to the same HTTP endpoint with different body contents and query arguments.

The _Consumer Backend_ and the _Connectors_ are off-the-shelf components that can be reused among different participants of the data space. This means that you don't actually need to implement any of these components yourself, just provide the appropriate configuration files.

![HTTP Pull example](./diagrams/http-pull-example.png "HTTP Pull example")

> The `consumer_sandbox` container is created solely for convenience and does not perform any specific tasks. Its purpose is to facilitate the execution of example scripts. Additionally, please note that the `/opt/src` directory contains the sources in this repository.

```console
vagrant@consumer:~$ docker exec -it consumer_sandbox python3 /opt/src/example/example_http_pull.py
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO Connecting to RabbitMQ at amqp://guest:guest@broker:5672
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO Declaring exchange edcpy-topic-exchange
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO Declaring queue http-pull-queue
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO Declaring queue http-push-queue
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO Starting broker
2023-06-26 06:32:05 e86fae31cbca edcpy.messaging[13] INFO `pull_handler` waiting for messages
2023-06-26 06:32:05 e86fae31cbca edcpy.orchestrator[13] INFO Preparing to transfer asset (query: GET-consumption)
2023-06-26 06:32:05 e86fae31cbca httpx[13] INFO HTTP Request: POST http://consumer.local:9193/management/v2/catalog/request "HTTP/1.1 200 OK"

[...]

2023-06-26 06:32:10 e86fae31cbca httpx[13] INFO HTTP Request: GET http://consumer.local:9291/public/ "HTTP/1.1 200 OK"
2023-06-26 06:32:10 e86fae31cbca __main__[13] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2023-06-25T00:00:00+00:00', 'value': 90},
             {'date': '2023-06-25T01:00:00+00:00', 'value': 98},
             {'date': '2023-06-25T02:00:00+00:00', 'value': 68},
             {'date': '2023-06-25T03:00:00+00:00', 'value': 13},
             {'date': '2023-06-25T04:00:00+00:00', 'value': 94},
             {'date': '2023-06-25T05:00:00+00:00', 'value': 16},
             {'date': '2023-06-25T06:00:00+00:00', 'value': 1},
             {'date': '2023-06-25T07:00:00+00:00', 'value': 6},
             {'date': '2023-06-25T08:00:00+00:00', 'value': 67},
             {'date': '2023-06-25T09:00:00+00:00', 'value': 33},
             {'date': '2023-06-25T10:00:00+00:00', 'value': 87},
             {'date': '2023-06-25T11:00:00+00:00', 'value': 56},
             {'date': '2023-06-25T12:00:00+00:00', 'value': 65},
             {'date': '2023-06-25T13:00:00+00:00', 'value': 65},
             {'date': '2023-06-25T14:00:00+00:00', 'value': 69},
             {'date': '2023-06-25T15:00:00+00:00', 'value': 96},
             {'date': '2023-06-25T16:00:00+00:00', 'value': 8},
             {'date': '2023-06-25T17:00:00+00:00', 'value': 14},
             {'date': '2023-06-25T18:00:00+00:00', 'value': 44},
             {'date': '2023-06-25T19:00:00+00:00', 'value': 21},
             {'date': '2023-06-25T20:00:00+00:00', 'value': 51},
             {'date': '2023-06-25T21:00:00+00:00', 'value': 8},
             {'date': '2023-06-25T22:00:00+00:00', 'value': 4},
             {'date': '2023-06-25T23:00:00+00:00', 'value': 39}]}
2023-06-26 06:32:10 e86fae31cbca edcpy.orchestrator[13] INFO Preparing to transfer asset (query: POST-consumption-prediction)

[...]

2023-06-26 06:32:15 e86fae31cbca httpx[13] INFO HTTP Request: POST http://consumer.local:9291/public/ "HTTP/1.1 200 OK"
2023-06-26 06:32:15 e86fae31cbca __main__[13] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2023-06-15T14:30:00+00:00', 'value': 67},
             {'date': '2023-06-15T15:30:00+00:00', 'value': 88},
             {'date': '2023-06-15T16:30:00+00:00', 'value': 29},
             {'date': '2023-06-15T17:30:00+00:00', 'value': 52}]}
```

### Provider Push

This example demonstrates the _Provider Push_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

![HTTP Push example](./diagrams/http-push-example.png "HTTP Push example")

```console
vagrant@consumer:~$ docker exec -it consumer_sandbox python3 /opt/src/example/example_http_push.py
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO Connecting to RabbitMQ at amqp://guest:guest@broker:5672
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO Declaring exchange edcpy-topic-exchange
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO Declaring queue http-pull-queue
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO Declaring queue http-push-queue
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO Starting broker
2023-06-22 17:11:35 16ea40c695f8 edcpy.messaging[13] INFO `push_handler` waiting for messages
2023-06-22 17:11:35 16ea40c695f8 edcpy.orchestrator[13] INFO Preparing to transfer asset (query: GET-consumption)
2023-06-22 17:11:35 16ea40c695f8 httpx[13] INFO HTTP Request: POST http://consumer.local:9193/management/v2/catalog/request "HTTP/1.1 200 OK"
2023-06-22 17:11:35 16ea40c695f8 httpx[13] INFO HTTP Request: POST http://consumer.local:9193/management/v2/contractnegotiations "HTTP/1.1 200 OK"
2023-06-22 17:11:35 16ea40c695f8 httpx[13] INFO HTTP Request: GET http://consumer.local:9193/management/v2/contractnegotiations/22343903-2f1e-4ba9-b8ad-ed3c2fe7736d "HTTP/1.1 200 OK"
2023-06-22 17:11:36 16ea40c695f8 httpx[13] INFO HTTP Request: GET http://consumer.local:9193/management/v2/contractnegotiations/22343903-2f1e-4ba9-b8ad-ed3c2fe7736d "HTTP/1.1 200 OK"
2023-06-22 17:11:36 16ea40c695f8 httpx[13] INFO HTTP Request: POST http://consumer.local:9193/management/v2/transferprocesses "HTTP/1.1 200 OK"
2023-06-22 17:11:36 16ea40c695f8 httpx[13] INFO HTTP Request: GET http://consumer.local:9193/management/v2/transferprocesses/ef840aaf-720e-4f16-8014-4d9c9dd6c201 "HTTP/1.1 200 OK"

[...]

2023-06-22 17:11:39 16ea40c695f8 __main__[13] INFO Received response from Mock HTTP API:
{'location': 'Asturias',
 'results': [{'date': '2023-06-21T00:00:00+00:00', 'value': 68},
             {'date': '2023-06-21T01:00:00+00:00', 'value': 42},
             {'date': '2023-06-21T02:00:00+00:00', 'value': 5},
             {'date': '2023-06-21T03:00:00+00:00', 'value': 6},
             {'date': '2023-06-21T04:00:00+00:00', 'value': 79},
             {'date': '2023-06-21T05:00:00+00:00', 'value': 71},
             {'date': '2023-06-21T06:00:00+00:00', 'value': 4},
             {'date': '2023-06-21T07:00:00+00:00', 'value': 83},
             {'date': '2023-06-21T08:00:00+00:00', 'value': 76},
             {'date': '2023-06-21T09:00:00+00:00', 'value': 69},
             {'date': '2023-06-21T10:00:00+00:00', 'value': 4},
             {'date': '2023-06-21T11:00:00+00:00', 'value': 14},
             {'date': '2023-06-21T12:00:00+00:00', 'value': 80},
             {'date': '2023-06-21T13:00:00+00:00', 'value': 64},
             {'date': '2023-06-21T14:00:00+00:00', 'value': 74},
             {'date': '2023-06-21T15:00:00+00:00', 'value': 22},
             {'date': '2023-06-21T16:00:00+00:00', 'value': 72},
             {'date': '2023-06-21T17:00:00+00:00', 'value': 100},
             {'date': '2023-06-21T18:00:00+00:00', 'value': 40},
             {'date': '2023-06-21T19:00:00+00:00', 'value': 84},
             {'date': '2023-06-21T20:00:00+00:00', 'value': 71},
             {'date': '2023-06-21T21:00:00+00:00', 'value': 16},
             {'date': '2023-06-21T22:00:00+00:00', 'value': 74},
             {'date': '2023-06-21T23:00:00+00:00', 'value': 52}]}
```

## Frequently Asked Questions

**How does the provider know how to expose the Mock HTTP API and create the related assets in the data space?**

The Mock HTTP API must expose a schema file that adheres to the [OpenAPI specifications](https://spec.openapis.org/oas/latest.html). The URL to this file is provided as a configuration property (`eu.datacellar.openapi.url`) to the provider. Upon initialization, the provider retrieves the schema file and builds the necessary assets.

The JSON file of the API schema serves as the authoritative source, determining how the HTTP API will be represented within the data space.

**What is the role of the RabbitMQ message broker?**

In both the _Consumer Pull_ and _Provider Push_ approaches, an HTTP server (i.e. _Consumer Backend_) needs to be running on the consumer's side.

In this project, [RabbitMQ](https://www.rabbitmq.com/) was chosen as a tool to decouple the messages received by the _Consumer Backend_ and enable arbitrary applications to subscribe to and process them asynchronously.

RabbitMQ was selected due to its popularity and ease of use as a message broker. Other options, such as Redis, could have been chosen as well. It's worth noting that a message broker is not strictly necessary. Any mechanism capable of passing the messages received on the _Consumer Backend_ to the application would be suitable.

**What is the `edcpy` package, and is Python required?**

The [Management](https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api/0.1.0-SNAPSHOT) and [Control](https://app.swaggerhub.com/apis/eclipse-edc-bot/control-api/0.1.0-SNAPSHOT) APIs of the Eclipse Connector involve complex interactions with multiple steps that need to be repeated. The `edcpy` package serves as a means to encapsulate this logic, making it reusable. Additionally, it provides a ready-to-use _Consumer Backend_ that integrates with RabbitMQ.

However, it's important to note that the use of Python is not mandatory. The `edcpy` package is designed to (hopefully) facilitate the development process, but if you prefer to use another programming language, you have the flexibility to build your own _Consumer Backend_ and directly communicate with the Management API.

**What are the minimum requirements that an HTTP API must have to be interoperable with the _Core Connector_?**

We will strive to ensure that the core connector is compatible with any arbitrary HTTP API, as long as it is properly described using the OpenAPI specification.

This means that you should have the liberty of using whatever technology stack you feel more comfortable with to develop the API.

**Are OpenAPI-based APIs the only supported data sources?**

Yes, for the time being. The _Core Connector_ is still in its early stages of development, and we are focusing on the most common use cases. However, we are open to expanding the scope of the project in the future.

In any case, the OpenAPI specification is flexible enough to describe a wide variety of APIs. It should be fairly simple to expose your existing data source as an OpenAPI-based API.

**Why was Keycloak used as the identity service instead of DAPS?**

The [Dynamic Attribute Provisioning Service (DAPS)](https://docs.internationaldataspaces.org/ids-knowledgebase/v/ids-ram-4/layers-of-the-reference-architecture-model/3-layers-of-the-reference-architecture-model/3_5_0_system_layer/3_5_1_identity_provider#dynamic-attribute-provisioning-service-daps) is one of the key building blocks regarding identity in an IDS data space. It would be the most suitable choice for ensuring full compliance within a data space.

However, this is a proof of concept aimed at demonstrating the capabilities of the _Core Connector_. As such, we decided to use [Keycloak](https://www.keycloak.org/) as an alternative to DAPS because it is more mature, and we are significantly more familiar with it.
