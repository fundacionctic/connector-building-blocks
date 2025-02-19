# Data Space Connector Building Blocks

- [Data Space Connector Building Blocks](#data-space-connector-building-blocks)
  - [Introduction](#introduction)
  - [Public Artifacts](#public-artifacts)
    - [Configuration of the Connector Image](#configuration-of-the-connector-image)
  - [Guides and Examples](#guides-and-examples)

> [!CAUTION]
> Please note that most of the code in this repository is still a work in progress and will thus likely go through several breaking changes throughout its development.

## Introduction

This repository contains a collection of software components that aim at simplifying the deployment of data space connectors based on the [Eclipse Dataspace Components](https://eclipse-edc.github.io/docs/#/) (EDC) ecosystem and the interactions of applications with those connectors. Specifically, the following components are provided here:

* An EDC connector extension capable of interpreting an OpenAPI schema and generating a set of assets within the data space to represent the services provided by a participant component. The underlying idea is to enable participants to develop their own HTTP APIs while the extension abstracts away the intricacies of exposing these HTTP APIs to the data space.
* An EDC connector extension that implements authentication via W3C Verifiable Credentials.
* A Python library that implements the logic to interact with the [Management](https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api) and [Control](https://app.swaggerhub.com/apis/eclipse-edc-bot/control-api) APIs of the EDC connector to go through the necessary steps to transfer data between two participants in the data space.

> [!TIP]
> Extensions are self-contained software components that add new functionalities to the connector. For example, there are extensions to add authentication based on OAuth2 and to enable the connector to serve files from S3 buckets. In this instance, we are developing our own connector extensions to tailor the connector to our specific use case. Check the [basic EDC connector samples](https://github.com/eclipse-edc/Samples/blob/main/basic/basic-02-health-endpoint/README.md) to get a better understanding of how extensions work.

The repository is organized as follows:

* The `connector` folder contains a Java project with a very early draft version of the connector extensions and a connector launcher.
* The `mock-backend` folder contains an example HTTP API as exposed by a data space participant. This API is described by an [OpenAPI](https://learn.openapis.org/) document. The logic of the component itself does not hold any value; its purpose is to demonstrate where each participant should contribute.
* The `edcpy` folder contains a Python package built on top of Poetry, providing a series of utilities to interact with a data space based on the EDC ecosystem. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process. Additionally, it offers an example implementation of a _consumer backend_.
* The `dev-config` and `example` folders, contain the configuration and scripts necessary to deploy a consumer and a provider, and to demonstrate end-to-end communications based on the Dataspace Protocol between them.

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
| `API_AUTH_KEY`         | The secret api key that the connector will use to authenticate requests to its Management API.                                 |

## Guides and Examples

| Example                                                                             | Description                                                                                                                                                               |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Minimal example](docs/index.md)                                                    | A minimal example demonstrating how to compile, configure the connector, and transfer data between a consumer and a provider.                                             |
| [Example with SSI extension](docs/example-identity-vc.md)                           | This example extends the minimal example to incorporate the SSI extension for authentication based on W3C Verifiable Credentials.                                         |
| [FAQs](docs/faqs.md)                                                                | Some frequently asked questions.                                                                                                                                          |
| [OpenAPI extension for presentation definitions](docs/openapi-credential-checks.md) | A proposal for extending an OpenAPI schema so that the connector is able to enforce policies that depend on participants having a specific type of Verifiable Credential. |
