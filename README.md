# Eclipse Dataspace Components Proof of Concept

This project contains a proof of concept that aims to automate the deployment of a Minimum Viable Dataspace and demonstrate how arbitrary data sources can be integrated into the Data Cellar dataspace using the Eclipse Dataspace Components software stack.

The approach taken here is that any Data Cellar participant component can expose an HTTP API described by a standard OpenAPI schema. Then, there is a Data Cellar Core Connector that is able to understand this schema and create a series of assets in the data space to represent the HTTP endpoints. These endpoints, in turn, provide access to the datasets and services offered by the participant component in question.

The repository is organized as follows:

* The `datacellar-connector` folder contains a Java project with several separate proofs-of-concept. Most of these are derived from and adapted from the [EDC samples repository](https://github.com/eclipse-edc/Samples). The most relevant code is located in the `datacellar-core-connector` folder, which contains a very early draft version of the _Data Cellar Core Connector_ extension
* The `datacellar-mock-component` folder contains an example Data Cellar participant that exposes both an HTTP API and an event-driven API based on RabbitMQ. These APIs are described by [OpenAPI](https://learn.openapis.org/) and [AsyncAPI](https://www.asyncapi.com/docs) documents, respectively. The logic of the component itself does not hold any value; its purpose is to demonstrate where each Data Cellar partner should contribute.
* The `edcpy` folder contains a Python package built on top of [Poetry](https://python-poetry.org/), providing a series of utilities to interact with an EDC-based dataspace. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process from start to finish. Additionally, it offers an example implementation of an [HTTP pull receiver](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane) backend.
* The `example` folder contains the configuration files required for the end-to-end example of an interaction between a provider and consumer. This example is one of the main contributions of this repository and aims to clarify any doubts or uncertainties regarding how to integrate a regular service or API into a data space.

## Example

[This Gist shows an example console log](https://gist.github.com/agmangas/ae64592f6319f34ffdce5626529001a0) that can be obtained after building and provisioning the [Vagrant](https://developer.hashicorp.com/vagrant/docs) boxes of the consumer and provider. The example demonstrates how to list the assets exposed by the provider, which are obtained from the HTTP API of the mock component. Then, the consumer uses the HTTP pull pattern to call an HTTP endpoint of the provider using the GET method.