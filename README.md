# Eclipse Dataspace Components Proof of Concept

This project contains a proof of concept that aims to automate the deployment of a Minimum Viable Dataspace and demonstrate how arbitrary data sources can be integrated into the Data Cellar dataspace using the Eclipse Dataspace Components software stack.

The approach taken here is that any Data Cellar participant component can expose an HTTP API described by a standard OpenAPI schema. Then, there is a Data Cellar Core Connector that is able to understand this schema and create a series of assets in the data space to represent the HTTP endpoints. These endpoints, in turn, provide access to the datasets and services offered by the participant component in question.

The repository is organized as follows:

* The `datacellar-connector` folder contains a Java project with several separate proofs-of-concept. Most of these are derived from and adapted from the [EDC samples repository](https://github.com/eclipse-edc/Samples). The most relevant code is located in the `datacellar-core-connector` folder, which contains a very early draft version of the _Data Cellar Core Connector_ extension
* The `datacellar-mock-component` folder contains an example Data Cellar participant that exposes both an HTTP API and an event-driven API based on RabbitMQ. These APIs are described by [OpenAPI](https://learn.openapis.org/) and [AsyncAPI](https://www.asyncapi.com/docs) documents, respectively. The logic of the component itself does not hold any value; its purpose is to demonstrate where each Data Cellar partner should contribute.
* The `edcpy` folder contains a Python package built on top of [Poetry](https://python-poetry.org/), providing a series of utilities to interact with an EDC-based dataspace. For example, it contains the logic to execute all the necessary HTTP requests to successfully complete a transfer process from start to finish. Additionally, it offers an example implementation of an [HTTP pull receiver](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane) backend.
* The `example` folder contains the configuration files required for the end-to-end example of an interaction between a provider and consumer. This example is one of the main contributions of this repository and aims to clarify any doubts or uncertainties regarding how to integrate a regular service or API into a data space.

## Examples

There is a `Vagrantfile` in the root of the repository, which serves as the configuration file for Vagrant. [Vagrant](https://www.vagrantup.com/) is a tool utilized here to generate reproducible versions of two separate Ubuntu Virtual Machines: one for the provider and another for the consumer. This approach guarantees that the examples portray a more realistic scenario where the consumer and provider are deployed on different instances. Consequently, this distinction is reflected in the configuration files, providing a more illustrative demonstration rather than relying only on localhost access for all configuration properties.

After installing Vagrant on your system, simply run `vagrant up` to create both the provider and the consumer. The `Vagrantfile` is configured to handle all the necessary provisioning steps, such as installing dependencies and building the connector. Once the build process is complete, you can log into the consumer and provider by using `vagrant ssh consumer` or `vagrant ssh provider`.

> Note that we use Multicast DNS to ensure that `provider.local` resolves to the provider’s IP and that `consumer.local` resolves to the consumers’ IP. This forces us to install `avahi-daemon` and `libnss-mdns` in both the consumer and provider, and also to bind the volumes `/var/run/dbus` and `/var/run/avahi-daemon/socket` on all Docker containers.

### Consumer Pull

This example demonstrates the _Consumer Pull_ use case as defined in the [documentation of the Transfer Data Plane extension](https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane).

This approach tends to be more efficient than the Provider Push approach, as a single access token can be reused to send multiple requests to the same HTTP endpoint with different body contents and query arguments.


![HTTP Pull example](./diagrams/http-pull-example.png "HTTP Pull example")

```console
vagrant@consumer:~$ docker exec -it datacellar_consumer_sandbox python /opt/src/example/example_http_pull.py
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
vagrant@consumer:~$ docker exec -it datacellar_consumer_sandbox python /opt/src/example/example_http_push.py
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO Connecting to RabbitMQ at amqp://guest:guest@broker:5672
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO Declaring exchange edcpy-topic-exchange
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO Declaring queue http-pull-queue
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO Declaring queue http-push-queue
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO Starting broker
2023-06-22 11:22:41 2567f5522989 edcpy.messaging[48] INFO `push_handler` waiting for messages
2023-06-22 11:22:41 2567f5522989 edcpy.orchestrator[48] INFO Preparing to transfer asset (query: GET-asyncapi-json)
2023-06-22 11:22:41 2567f5522989 httpx[48] INFO HTTP Request: POST http://consumer.local:9193/management/v2/catalog/request "HTTP/1.1 200 OK"
2023-06-22 11:22:41 2567f5522989 httpx[48] INFO HTTP Request: POST http://consumer.local:9193/management/v2/contractnegotiations "HTTP/1.1 200 OK"
2023-06-22 11:22:41 2567f5522989 httpx[48] INFO HTTP Request: GET http://consumer.local:9193/management/v2/contractnegotiations/58e6d5ec-7523-4aec-a24a-dc50b0f9f69d "HTTP/1.1 200 OK"

[...]

2023-06-22 11:22:45 2567f5522989 __main__[48] INFO Received response from Mock HTTP API:
{'asyncapi': '2.6.0',
 'channels': {'aggregation-task': {'bindings': {'amqp': {'exchange': {'autoDelete': True,
                                                                      'name': 'tasks-exchange',
                                                                      'type': 'direct'},
                                                         'is': 'queue',
                                                         'queue': {'autoDelete': True,
                                                                   'name': 'aggregation-task-queue'}}},
                                   'publish': {'message': {'$ref': '#/components/messages/ConsumptionAggregationTaskMessage'}, [...]
```