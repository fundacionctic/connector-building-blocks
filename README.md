# Eclipse Dataspace Components Proof of Concept

- [Eclipse Dataspace Components Proof of Concept](#eclipse-dataspace-components-proof-of-concept)
  - [Introduction](#introduction)
  - [Public Artifacts](#public-artifacts)
    - [Configuration of the Connector Image](#configuration-of-the-connector-image)
  - [Examples](#examples)
    - [Prerequisites](#prerequisites)
    - [Consumer Pull](#consumer-pull)
    - [Provider Push](#provider-push)
  - [Frequently Asked Questions](#frequently-asked-questions)

> [!IMPORTANT]
> The previous IAM solution, which relied on OAuth 2 and Keycloak, will be replaced by another extension that aligns more closely with SSI principles. In this new extension, participants will authenticate themselves using W3C Verifiable Credentials. This is still a work in progress.

## Introduction

This project contains a proof of concept that aims to automate the deployment of a Minimum Viable Dataspace and demonstrate how arbitrary data sources can be integrated into the data space using the Eclipse Dataspace Components software stack.

The approach taken here is that **any data space participant component can expose an HTTP API described by a standard OpenAPI schema**. Then, there is a Core Connector that is able to understand this schema and create a series of assets in the data space to represent the HTTP endpoints. These endpoints, in turn, provide access to the datasets and services offered by the participant component in question.

The repository is organized as follows:

* The `connector` folder contains a Java project with a very early draft version of the _Core Connector_ extension. This extension is responsible for creating the assets in the data space based on the OpenAPI schema of the participant component.
* The `mock-backend` folder contains an example HTTP API as exposed by a data space participant. This API is described by an [OpenAPI](https://learn.openapis.org/) document. The logic of the component itself does not hold any value; its purpose is to demonstrate where each participant should contribute.
* The `edcpy` folder contains a Python package built on top of Poetry, providing a series of utilities to interact with an EDC-based dataspace. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process. Additionally, it offers an example implementation of a [Consumer Backend](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).
* The `dev-config` and `example` folders, alongside the `Vagrantfile`, contain the configuration and scripts necessary to deploy a consumer and a provider, and to demonstrate end-to-end communications based on the Dataspace Protocol between them.

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

## Examples

There is a `Vagrantfile` in the root of the repository, which serves as the configuration file for Vagrant. [Vagrant](https://www.vagrantup.com/) is a tool utilized here to generate reproducible versions of two separate Ubuntu Virtual Machines: one for the provider and another for the consumer. This approach guarantees that the examples portray a more realistic scenario where the consumer and provider are deployed on different instances. Consequently, this distinction is reflected in the configuration files, providing a more illustrative demonstration rather than relying only on localhost access for all configuration properties.

After installing Vagrant on your system, simply run `vagrant up` to create both the provider and the consumer. The `Vagrantfile` is configured to handle all the necessary provisioning steps, such as installing dependencies and building the connector. Once the build process is complete, you can log into the consumer and provider by using `vagrant ssh consumer` or `vagrant ssh provider`.

We use Multicast DNS to ensure that `provider.local` resolves to the provider’s IP and that `consumer.local` resolves to the consumers’ IP. This forces us to install `avahi-daemon` and `libnss-mdns` in both the consumer and provider, and also to bind the volumes `/var/run/dbus` and `/var/run/avahi-daemon/socket` on all Docker containers.

The following examples demonstrate two distinct approaches, which are summarized in the table below for clarity:

| Approach          | Key Characteristics                                                                                                                                              |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Provider Push** | The provider pushes data to the consumer by sending HTTP requests to the consumer's backend directly. These requests contain the responses from the mock API.    |
| **Consumer Pull** | The consumer pulls data from the provider by sending HTTP requests to the provider’s data plane public API. The provider proxies these requests to the mock API. |

> [!TIP]
> Please note that the example scripts should be run in the Consumer VM, which can be accessed by running `vagrant ssh consumer`.

### Prerequisites

* [VirtualBox](https://www.virtualbox.org/wiki/Downloads): a popular virtualization product.
* [Vagrant](https://developer.hashicorp.com/vagrant/downloads): a command line tool for managing virtual machines.

You just need to download and install the releases for your operating system. Vagrant should be able to find and use the [VirtualBox provider](https://developer.hashicorp.com/vagrant/docs/providers/virtualbox) automatically.

There are no other prerequisites, as Vagrant will take care of installing all the necessary dependencies inside the virtual machines.

### Consumer Pull

This example demonstrates the _Consumer Pull_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

In this pattern, a single access token can be reused to send multiple requests to the same HTTP endpoint with different body contents and query arguments.

The _Consumer Backend_ and the _Connectors_ are off-the-shelf components that can be reused among different participants of the data space. This means that you don't actually need to implement any of these components yourself, just provide the appropriate configuration files.

![HTTP Pull example](./diagrams/http-pull-example.png "HTTP Pull example")

```console
vagrant@consumer:~$ cd /vagrant/
vagrant@consumer:/vagrant$ task run-pull-example-from-consumer

[...]

task: [run-pull-example-from-consumer] $HOME/edc-venv/bin/python /vagrant/example/example_pull.py

[...]

2024-02-23 09:28:55 consumer __main__[41499] INFO Sending HTTP GET request with arguments:
{'headers': {'Authorization': 'eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3MDg2ODExMzUsImRhZCI6IntcInByb3BlcnRpZXNcIjp7XCJwYXRoXCI6XCIvY29uc3VtcHRpb25cIixcIm1ldGhvZFwiOlwiR0VUXCIsXCJodHRwczovL3czaWQub3JnL2VkYy92MC4wLjEvbnMvdHlwZVwiOlwiSHR0cERhdGFcIixcInByb3h5UXVlcnlQYXJhbXNcIjpcInRydWVcIixcIm5hbWVcIjpcImRhdGEtYWRkcmVzcy1HRVQtY29uc3VtcHRpb25cIixcInByb3h5Qm9keVwiOlwidHJ1ZVwiLFwiY29udGVudFR5cGVcIjpcImFwcGxpY2F0aW9uL2pzb25cIixcImh0dHBzOi8vdzNpZC5vcmcvZWRjL3YwLjAuMS9ucy9iYXNlVXJsXCI6XCJodHRwOi8vcHJvdmlkZXIubG9jYWw6OTA5MFwifX0ifQ.TqHNY3kwP7eB64tmTMkTv5jsvQElp3A2_i10bjDdKzrkFxuphcOJC__B040x2OVF_UlafFpb-0vM9bhUgp7zsTH0FG0pzTB-AmrZWVByKHm6vl1XzSvd8uRZdOyHREsIHEPzYtejnHJC-qcx4gIfH3n7n9x6sBlzY4ALdB_PAlSrDSjB7vXzSTkj2mujxjOnwdY-hX6XjFe_HLktH0BBJYFTh7W0rREEbaNl9PjQPrH2vf2mbfOFLAcKbdR7_zXPhhHhaiEAgQIClUbBQ5T2tGhZ0SSEtd1VG-lNpqunUoZRgtqDLni0dMsHvZuDZPqs1vXEmjUgwD300ucGaEDtTpbArHQZS2RazxFbzY9P947afw8qPlokzbEiOZ-7fZJbGkwViAzXuDxP9cWH5iAMOYgJJ8uSFc-m7oq8k7lRsjOGMcgHzNcNNgbe0Uk9iRuZdEuf1IxgWftACJUjdkHQLln3TNUuYHTftJViLWgL3ACKbbs4sHaNJK8cWUIf6AxG2E4omN-4lQGld94ziDn2Z_T58IyQJqRFHLC4g9bwbRH8Ntl1WzkucH6eIk5FgN4-8YgZHgOThAgRBUr4dn164HUJoJ9kilHV-d2QfunYu-1sgFGzCENtNv0oRT4iw6Ha5uAu9dk7Idm5Wk7xkwuU46ojVAqRCmRNT3DeHQ92oqQ'},
 'method': 'GET',
 'url': 'http://provider.local:9291/public/'}

[...]

2024-02-23 09:28:56 consumer __main__[41499] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2024-02-22T00:00:00+00:00', 'value': 53},
             {'date': '2024-02-22T01:00:00+00:00', 'value': 62},
             {'date': '2024-02-22T02:00:00+00:00', 'value': 10},
             {'date': '2024-02-22T03:00:00+00:00', 'value': 73},
             {'date': '2024-02-22T04:00:00+00:00', 'value': 22},
             {'date': '2024-02-22T05:00:00+00:00', 'value': 72},
             {'date': '2024-02-22T06:00:00+00:00', 'value': 98},
             {'date': '2024-02-22T07:00:00+00:00', 'value': 80},
             {'date': '2024-02-22T08:00:00+00:00', 'value': 39},
             {'date': '2024-02-22T09:00:00+00:00', 'value': 77},
             {'date': '2024-02-22T10:00:00+00:00', 'value': 88},
             {'date': '2024-02-22T11:00:00+00:00', 'value': 7},
             {'date': '2024-02-22T12:00:00+00:00', 'value': 80},
             {'date': '2024-02-22T13:00:00+00:00', 'value': 74},
             {'date': '2024-02-22T14:00:00+00:00', 'value': 94},
             {'date': '2024-02-22T15:00:00+00:00', 'value': 49},
             {'date': '2024-02-22T16:00:00+00:00', 'value': 7},
             {'date': '2024-02-22T17:00:00+00:00', 'value': 87},
             {'date': '2024-02-22T18:00:00+00:00', 'value': 14},
             {'date': '2024-02-22T19:00:00+00:00', 'value': 27},
             {'date': '2024-02-22T20:00:00+00:00', 'value': 0},
             {'date': '2024-02-22T21:00:00+00:00', 'value': 60},
             {'date': '2024-02-22T22:00:00+00:00', 'value': 3},
             {'date': '2024-02-22T23:00:00+00:00', 'value': 93}]}

[...]

2024-02-23 09:28:59 consumer __main__[41499] INFO Sending HTTP POST request with arguments:
{'headers': {'Authorization': 'eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3MDg2ODExMzksImRhZCI6IntcInByb3BlcnRpZXNcIjp7XCJwYXRoXCI6XCIvY29uc3VtcHRpb24vcHJlZGljdGlvblwiLFwibWV0aG9kXCI6XCJQT1NUXCIsXCJodHRwczovL3czaWQub3JnL2VkYy92MC4wLjEvbnMvdHlwZVwiOlwiSHR0cERhdGFcIixcInByb3h5UXVlcnlQYXJhbXNcIjpcInRydWVcIixcIm5hbWVcIjpcImRhdGEtYWRkcmVzcy1QT1NULWNvbnN1bXB0aW9uLXByZWRpY3Rpb25cIixcInByb3h5Qm9keVwiOlwidHJ1ZVwiLFwiY29udGVudFR5cGVcIjpcImFwcGxpY2F0aW9uL2pzb25cIixcImh0dHBzOi8vdzNpZC5vcmcvZWRjL3YwLjAuMS9ucy9iYXNlVXJsXCI6XCJodHRwOi8vcHJvdmlkZXIubG9jYWw6OTA5MFwifX0ifQ.agOUe_CM2T_bTGNsPgggkvgvusMInsIipnP66tgemHoy6WmoIEomhSY9FLzjjjOSwXEH1mZg2PPUPk7Bkbzh9Cnz75RFsGvruvaFiwLbREcXQFLfD_dtvHBSdAtf2ufAulS9e0CzsLqUrwpY934kn0RmKFnQyOfCdQJrIF_kD2loy3J56ygKXYKpQuw_U4QMoM2UW4QjIFJ8jhkIAfmU2hNZi7-UHM-AM-2TZXRQnBD76unMlbki_iA4HMdjmRb6iwAIPpgmOEnctYcGYdhH0v9MTBcMhKcdlQ8i9MTYa-1YkzOIFgAu3E4pt_GM1cDiQxbU2u2sCD9daCRk39UxRTcqgv2XLQ8T8XSgPzIbEaJ19cNb-3TIq1Tw29c9y7mD7delbtMQiGyGcT6dthcfIGOdPH6aUnvWUzikGRgWo9Npd-O5o1VEwLROTPaHUyl6nAlWscwm1_P6vDhppql39layUDk2qcc5bkNOLkxKK2Z6PSFSkAhdN3nE2y_Tz8kbgtu8-CQefaNs2rLkkObxN89M9bszg4AxToxKpBSOIMfZMNAtpr5OtHj3zZluLd_cQJl-U-hQVm7NqGy1-KGBY575PJlCKtr5iEIXJKf5oD2viLiqFTx7s080CGToGBOxdmj3slExU3HI4xIKyzN1nCpw_AjxhlR72z2Z-iBoMK8'},
 'json': {'date_from': '2023-06-15T14:30:00',
          'date_to': '2023-06-15T18:00:00',
          'location': 'Asturias'},
 'method': 'POST',
 'url': 'http://provider.local:9291/public/'}

[...]

2024-02-23 09:29:00 consumer __main__[41499] INFO Response:
{'location': 'Asturias',
 'results': [{'date': '2023-06-15T14:30:00+00:00', 'value': 16},
             {'date': '2023-06-15T15:30:00+00:00', 'value': 4},
             {'date': '2023-06-15T16:30:00+00:00', 'value': 49},
             {'date': '2023-06-15T17:30:00+00:00', 'value': 1}]}

[...]
```

### Provider Push

This example demonstrates the _Provider Push_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

![HTTP Push example](./diagrams/http-push-example.png "HTTP Push example")

```console
vagrant@consumer:/vagrant$ task run-push-example-from-consumer

[...]

task: [run-push-example-from-consumer] $HOME/edc-venv/bin/python /vagrant/example/example_push.py

[...]

2024-02-23 09:33:03 consumer __main__[41771] INFO Received response from Mock Backend HTTP API:
{'location': 'Asturias',
 'results': [{'date': '2024-02-22T00:00:00+00:00', 'value': 85},
             {'date': '2024-02-22T01:00:00+00:00', 'value': 77},
             {'date': '2024-02-22T02:00:00+00:00', 'value': 63},
             {'date': '2024-02-22T03:00:00+00:00', 'value': 16},
             {'date': '2024-02-22T04:00:00+00:00', 'value': 10},
             {'date': '2024-02-22T05:00:00+00:00', 'value': 36},
             {'date': '2024-02-22T06:00:00+00:00', 'value': 46},
             {'date': '2024-02-22T07:00:00+00:00', 'value': 48},
             {'date': '2024-02-22T08:00:00+00:00', 'value': 9},
             {'date': '2024-02-22T09:00:00+00:00', 'value': 50},
             {'date': '2024-02-22T10:00:00+00:00', 'value': 12},
             {'date': '2024-02-22T11:00:00+00:00', 'value': 70},
             {'date': '2024-02-22T12:00:00+00:00', 'value': 41},
             {'date': '2024-02-22T13:00:00+00:00', 'value': 59},
             {'date': '2024-02-22T14:00:00+00:00', 'value': 63},
             {'date': '2024-02-22T15:00:00+00:00', 'value': 86},
             {'date': '2024-02-22T16:00:00+00:00', 'value': 100},
             {'date': '2024-02-22T17:00:00+00:00', 'value': 34},
             {'date': '2024-02-22T18:00:00+00:00', 'value': 81},
             {'date': '2024-02-22T19:00:00+00:00', 'value': 55},
             {'date': '2024-02-22T20:00:00+00:00', 'value': 49},
             {'date': '2024-02-22T21:00:00+00:00', 'value': 58},
             {'date': '2024-02-22T22:00:00+00:00', 'value': 41},
             {'date': '2024-02-22T23:00:00+00:00', 'value': 89}]}

[...]
```

## Frequently Asked Questions

**How does the provider know how to expose the Mock Backend HTTP API and create the related assets in the data space?**

The Mock Backend HTTP API must expose a schema file that adheres to the [OpenAPI specifications](https://spec.openapis.org/oas/latest.html). The URL to this file is provided as a configuration property (`eu.datacellar.openapi.url`) to the provider. Upon initialization, the provider retrieves the schema file and builds the necessary assets.

The JSON file of the API schema serves as the authoritative source, determining how the HTTP API will be represented within the data space.

**What is the role of the RabbitMQ message broker?**

In both the _Consumer Pull_ and _Provider Push_ approaches, an HTTP server (i.e. _Consumer Backend_) needs to be running on the consumer's side.

In this project, [RabbitMQ](https://www.rabbitmq.com/) was chosen as a tool to decouple the messages received by the _Consumer Backend_ and enable arbitrary applications to subscribe to and process them asynchronously.

RabbitMQ was selected due to its popularity and ease of use as a message broker. Other options, such as Redis, could have been chosen as well. It's worth noting that a message broker is not strictly necessary. Any mechanism capable of passing the messages received on the _Consumer Backend_ to the application would be suitable.

**What is the `edcpy` package, and is Python required?**

The [Management](https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api) and [Control](https://app.swaggerhub.com/apis/eclipse-edc-bot/control-api) APIs of the Eclipse Connector involve complex interactions with multiple requests. The `edcpy` package serves as a means to encapsulate this logic, making it reusable. Additionally, it provides a ready-to-use _Consumer Backend_ that integrates with RabbitMQ.

However, it's important to note that the use of Python is not mandatory. The `edcpy` package is designed to (hopefully) facilitate the development process, but if you prefer to use another programming language, you have the flexibility to build your own _Consumer Backend_ and directly communicate with the Management API.

**What are the minimum requirements that an HTTP API must have to be interoperable with the _Core Connector_?**

We will strive to ensure that the core connector is compatible with any arbitrary HTTP API, as long as it is properly described using the OpenAPI specification.

This means that you should have the liberty of using whatever technology stack you feel more comfortable with to develop the API.

**Are OpenAPI-based APIs the only supported data sources?**

Yes, for the time being. The _Core Connector_ is still in its early stages of development, and we are focusing on the most common use cases. However, we are open to expanding the scope of the project in the future.

In any case, the OpenAPI specification is flexible enough to describe a wide variety of APIs. It should be fairly simple to expose your existing data source as an OpenAPI-based API.