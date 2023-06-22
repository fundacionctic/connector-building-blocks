# Eclipse Dataspace Components Proof of Concept

This project contains a proof of concept that aims to automate the deployment of a Minimum Viable Dataspace and demonstrate how arbitrary data sources can be integrated into the data space using the Eclipse Dataspace Components software stack.

The approach taken here is that any data space participant component can expose an HTTP API described by a standard OpenAPI schema. Then, there is a Core Connector that is able to understand this schema and create a series of assets in the data space to represent the HTTP endpoints. These endpoints, in turn, provide access to the datasets and services offered by the participant component in question.

The repository is organized as follows:

* The `connector` folder contains a Java project with several separate proofs-of-concept. Most of these are derived from and adapted from the [EDC samples repository](https://github.com/eclipse-edc/Samples). The most relevant code is located in the `core-connector` folder, which contains a very early draft version of the _Core Connector_ extension
* The `mock-component` folder contains an example data space participant that exposes both an HTTP API and an event-driven API based on RabbitMQ. These APIs are described by [OpenAPI](https://learn.openapis.org/) and [AsyncAPI](https://www.asyncapi.com/docs) documents, respectively. The logic of the component itself does not hold any value; its purpose is to demonstrate where each partner should contribute.

> Support for AsyncAPI and event-driven APIs is a nice-to-have that is not currently being prioritized. It will be addressed at a later stage if time permits and there are no technological roadblocks.

* The `edcpy` folder contains a Python package built on top of [Poetry](https://python-poetry.org/), providing a series of utilities to interact with an EDC-based dataspace. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process from start to finish. Additionally, it offers an example implementation of an [HTTP pull receiver](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane) backend.
* The `example` folder contains the configuration files required for the end-to-end example of an interaction between a provider and consumer. This example is one of the main contributions of this repository and aims to clarify any doubts or uncertainties regarding how to integrate a regular service or API into a data space.

## Examples

There is a `Vagrantfile` in the root of the repository, which serves as the configuration file for Vagrant. [Vagrant](https://www.vagrantup.com/) is a tool utilized here to generate reproducible versions of two separate Ubuntu Virtual Machines: one for the provider and another for the consumer. This approach guarantees that the examples portray a more realistic scenario where the consumer and provider are deployed on different instances. Consequently, this distinction is reflected in the configuration files, providing a more illustrative demonstration rather than relying only on localhost access for all configuration properties.

After installing Vagrant on your system, simply run `vagrant up` to create both the provider and the consumer. The `Vagrantfile` is configured to handle all the necessary provisioning steps, such as installing dependencies and building the connector. Once the build process is complete, you can log into the consumer and provider by using `vagrant ssh consumer` or `vagrant ssh provider`.

We use Multicast DNS to ensure that `provider.local` resolves to the provider’s IP and that `consumer.local` resolves to the consumers’ IP. This forces us to install `avahi-daemon` and `libnss-mdns` in both the consumer and provider, and also to bind the volumes `/var/run/dbus` and `/var/run/avahi-daemon/socket` on all Docker containers.

> Please note that the examples below are run in the Consumer VM, which can be accessed by running `vagrant ssh consumer`.

### Consumer Pull

This example demonstrates the _Consumer Pull_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

This approach tends to be more efficient than the _Provider Push_ approach, as a single access token can be reused to send multiple requests to the same HTTP endpoint with different body contents and query arguments.

![HTTP Pull example](./diagrams/http-pull-example.png "HTTP Pull example")

> The `consumer_sandbox` container is created solely for convenience and does not perform any specific tasks. Its purpose is to facilitate the execution of example scripts. Additionally, please note that the `/opt/src` directory contains the sources in this repository.

```console
vagrant@consumer:~$ docker exec -it consumer_sandbox python /opt/src/example/example_http_pull.py
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO Connecting to RabbitMQ at amqp://guest:guest@broker:5672
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO Declaring exchange edcpy-topic-exchange
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO Declaring queue http-pull-queue
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO Declaring queue http-push-queue
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO Starting broker
2023-06-22 11:17:20 2567f5522989 edcpy.messaging[34] INFO `pull_handler` waiting for messages
2023-06-22 11:17:20 2567f5522989 edcpy.orchestrator[34] INFO Preparing to transfer asset (query: asyncapi-json)
2023-06-22 11:17:20 2567f5522989 httpx[34] INFO HTTP Request: POST http://consumer.local:9193/management/v2/catalog/request "HTTP/1.1 200 OK"

[...]

2023-06-22 11:17:25 2567f5522989 httpx[34] INFO HTTP Request: GET http://consumer.local:9291/public/ "HTTP/1.1 200 OK"

[...]

2023-06-22 11:17:25 2567f5522989 edcpy.orchestrator[34] INFO Preparing to transfer asset (query: consumption-prediction)

[...]

2023-06-22 11:17:29 2567f5522989 httpx[34] INFO HTTP Request: POST http://consumer.local:9291/public/ "HTTP/1.1 200 OK"
2023-06-22 11:17:29 2567f5522989 __main__[34] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2023-06-15T14:30:00+00:00', 'value': 19},
             {'date': '2023-06-15T15:30:00+00:00', 'value': 32},
             {'date': '2023-06-15T16:30:00+00:00', 'value': 90},
             {'date': '2023-06-15T17:30:00+00:00', 'value': 72}]}
```

### Provider Push

This example demonstrates the _Provider Push_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

![HTTP Push example](./diagrams/http-push-example.png "HTTP Push example")

```console
vagrant@consumer:~$ docker exec -it consumer_sandbox python /opt/src/example/example_http_push.py
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