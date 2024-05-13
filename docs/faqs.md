# Frequently Asked Questions

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

**What are the minimum requirements that an HTTP API must have to be interoperable with the OpenAPI connector extension?**

We will strive to ensure that our connector is compatible with any arbitrary HTTP API, as long as it is properly described using the OpenAPI specification.

This means that you should have the liberty of using whatever technology stack you feel more comfortable with to develop the API.

**Are OpenAPI-based APIs the only supported data sources?**

Yes, for the time being. These connector extensions are still in their early stages of development, and we are focusing on the most common use cases. However, we are open to expanding the scope of the project in the future.

In any case, the OpenAPI specification is flexible enough to describe a wide variety of APIs. It should be fairly simple to expose your existing data source as an OpenAPI-based API.
