# Self-Sovereign Identity Extension Example

This guide shows how to run the [minimal example](index.md) using the SSI extension to enable authentication between connectors using W3C Verifiable Credentials.

## Configure the connectors

There are two configuration files in the `dev-config` folder: `dev-consumer.properties` and `dev-provider.properties`. These files contain the configuration for the consumer and provider connectors, respectively.

Most of the configuration properties in those files are already explained in the main README. However, there are some new `eu.datacellar.*` properties that are related to the SSI identity extension. For example, in the case of the consumer connector:

```properties
eu.datacellar.wallet.url=http://host.docker.internal:7001
eu.datacellar.wallet.email=consumer@ctic.es
eu.datacellar.wallet.password=consumer
eu.datacellar.trust.did=did:web:gaiax.cticpoc.com:anchor
eu.datacellar.uniresolver.url=https://uniresolver.test.ctic.es/1.0/identifiers
```

| Property                        | Description                                                                                                                                                                                   |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `eu.datacellar.wallet.url`      | The URL of the wallet API.                                                                                                                                                                    |
| `eu.datacellar.wallet.email`    | The email of the wallet administrator user.                                                                                                                                                   |
| `eu.datacellar.wallet.password` | The password of the wallet administrator user.                                                                                                                                                |
| `eu.datacellar.trust.did`       | The DID of the trust anchor that the consumer connector trusts.                                                                                                                               |
| `eu.datacellar.uniresolver.url` | The URL of an instance of the [DIF Universal Resolver](https://github.com/decentralized-identity/universal-resolver). This service is leveraged by connectors to resolve DIDs to public keys. |

You only need to update the `eu.datacellar.uniresolver.url` to point to a running instance of the Universal Resolver. The default value points to a development instance in CTIC's test environment, which may not be available. The rest of the values should match the default configuration throughout the example.

> [!TIP]
> There's a development instance of the Universal Resolver available here, which may be used for testing purposes: [https://dev.uniresolver.io/](https://dev.uniresolver.io/). Please note that this is a development instance and thus may be unstable.

> [!IMPORTANT]
> If you update the wallet administrator credentials in the configuration files described below, please ensure that you also update these property files accordingly.

## Start the Connectors and Associated Services

You need the following requirements to run the example:

* [Taskfile](https://taskfile.dev/)
* Python 3
* Virtualenv
* [Poetry](https://python-poetry.org/)
* Docker
* Java
* Gradle

> [!NOTE]
> The example has been tested with Java 21, although it should work with 17+.

```console
$ SSI=true task dev-up

[...]

task: [create-certs] docker run --rm -v /home/connector-building-blocks/dev-config/certs-provider:/out edc-poc-scripts /bin/bash -c "OUT_DIR=/out KEY_ALIAS=datacellar KEY_PASSW=datacellar ./create-certs.sh"

[...]

task: [build-connector] gradle  build
Starting a Gradle Daemon (subsequent builds will be faster)

BUILD SUCCESSFUL in 16s
22 actionable tasks: 22 executed
task: [dev-up] docker compose -f /home/connector-building-blocks/docker-compose-dev.yml up --force-recreate -d --build --wait

[...]
```

This task will perform the following actions:

* Create the keys and certificate for the provider and consumer connectors.
* Start the Compose stack for the Mock HTTP API, serving as the API backend for the provider connector.
* Build the Gradle project of the connector. The `SSI=true` environment variable is set to enable the SSI extension, allowing connectors to build, exchange, and validate Verifiable Presentations for authentication purposes.
* Start the development Compose stack with all services, including consumer and provider connectors, wallets, and consumer message broker.

After the task finishes, you should see the following services running:

```console
$ docker compose -f docker-compose-dev.yml ps
NAME               IMAGE                                         COMMAND                  SERVICE            CREATED         STATUS                            PORTS
anchor_wallet      waltid/wallet-api:1.0.2402271122-SNAPSHOT     "/waltid-wallet-api/…"   anchor_wallet      4 minutes ago   Up 4 minutes                      0.0.0.0:7051->7001/tcp
consumer           edc-dev-jdk                                   "java -Dedc.fs.confi…"   consumer           4 minutes ago   Restarting (255) 54 seconds ago
consumer_backend   edc-dev-edcpy                                 "run-http-backend"       consumer_backend   4 minutes ago   Up 4 minutes                      0.0.0.0:28000->28000/tcp
consumer_broker    rabbitmq:3.11-management                      "docker-entrypoint.s…"   consumer_broker    4 minutes ago   Up 4 minutes                      4369/tcp, 5671/tcp, 0.0.0.0:5672->5672/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 0.0.0.0:15672->15672/tcp
consumer_wallet    waltid/wallet-api:1.0.2402271122-SNAPSHOT     "/waltid-wallet-api/…"   consumer_wallet    4 minutes ago   Up 4 minutes                      0.0.0.0:7001->7001/tcp
issuer             waltid/issuer-api:1.0.2402271122-SNAPSHOT     "/waltid-issuer-api/…"   issuer             4 minutes ago   Up 4 minutes                      0.0.0.0:7002->7002/tcp
provider           edc-dev-jdk                                   "java -Dedc.fs.confi…"   provider           4 minutes ago   Restarting (255) 54 seconds ago
provider_wallet    waltid/wallet-api:1.0.2402271122-SNAPSHOT     "/waltid-wallet-api/…"   provider_wallet    4 minutes ago   Up 4 minutes                      0.0.0.0:7061->7001/tcp
verifier           waltid/verifier-api:1.0.2402271122-SNAPSHOT   "/waltid-verifier-ap…"   verifier           4 minutes ago   Up 4 minutes                      0.0.0.0:7003->7003/tcp
```

You will notice that the `consumer` and `provider` containers are constantly restarting. This is because they are attempting to connect to the wallets, which have not yet been provisioned. Now, we need to execute the wallet provisioning script.

## Provision the Wallets

During the wallet provisioning process, the DIDs associated with the previously created public keys will be registered on a public web server, following the specification defined by the `did:web` method. The details of this web server are defined in the dotenv file `dev-config/.env.dev.wallets.local`. You must ensure that this file exists and contains at least the following environment variables:

> [!TIP]
> This file is not included in the repository, so you must create it manually.

```properties
DID_WEB_DOMAIN=example.com
DID_WEB_WEBSERVER_BASE_PATH=/home/user/htdocs
```

The `DID_WEB_WEBSERVER_BASE_PATH` variable is the web server base path where the DID documents will be stored. For example if the value is `/home/user/htdocs`, the DID for the consumer connector will be stored in the file `/home/user/htdocs/consumer/did.json` and the DID URL will be `did:web:example.com:consumer`.

> [!IMPORTANT]
> The web server needs to be exposed on port 80 and accessible from the internet.

To this end, the wallet provisioning script requires SSH access to the server at `DID_WEB_DOMAIN` via the default SSH key associated with the current user. You must ensure that your key is included in the `authorized_keys` file on the server. In other words, you should be able to log in to the server as follows:

```console
ssh example.com
```

There is also another configuration file for the wallet provisioning script: `dev-config/.env.dev.wallets`. You shouldn't need to modify this file, but you may change the usernames, passwords, or emails of the administrator users of the wallets if desired.

Once the previously mentioned configuration files are in place, you can proceed to run the task to provision the wallets. This will create a virtual environment with the required Python dependencies before executing the script:

```console
$ task dev-provision-wallets
task: [dev-provision-wallets-venv] virtualenv --python python3 /home/connector-building-blocks/scripts/.venv

[...]

task: [dev-provision-wallets] /home/connector-building-blocks/scripts/.venv/bin/python /home/connector-building-blocks/scripts/provision-wallets.py

[...]
```

This task will perform the following actions:

* Create an admin user in each of the three wallets: anchor, consumer, and provider.
* Create and import a key for each of the three wallets. Create a DID that is associated with that keypair.
* Register the DIDs using the `did:web` method as described above.
* Issue a Verifiable Credential that is signed by the anchor for the consumer and provider DIDs. This issuance is based on OID4VC.

## Run the Example Script

The example script at `example/example_catalogue.py` demonstrates how to use the consumer connector to fetch the catalogue from the provider connector. This is a simple example that serves to illustrate how connectors can authenticate each other using Verifiable Presentations.

First, you need to install the dependencies of the `edcpy` Python package, which implements the logic to interact with the HTTP APIs of EDC connectors:

```console
$ cd edcpy
$ poetry install

[...]

Installing the current project: edcpy (0.2.0a0)
```

The `edcpy` package reads the configuration from the environment variables defined in the `dev-config/.env.dev.consumer` file. To export these variables, you can use the following command:

```console
export $(grep -v '^#' ../dev-config/.env.dev.consumer | xargs)
```

Now you can run the example script:

```console
$ poetry run python ../example/example_catalogue.py

[...]

2024-04-04 14:17:43 msi-1526.fundacionctic.org __main__[33757] INFO Found datasets:
[{'@id': 'POST-consumption-prediction',
  '@type': 'dcat:Dataset',
  'dcat:distribution': [{'@type': 'dcat:Distribution',
                         'dcat:accessService': 'cbf06dd5-9c94-4a05-b40e-d9d3a81ed633',
                         'dct:format': {'@id': 'HttpProxy'}},
                        {'@type': 'dcat:Distribution',
                         'dcat:accessService': 'cbf06dd5-9c94-4a05-b40e-d9d3a81ed633',
                         'dct:format': {'@id': 'HttpData'}}],
  'id': 'POST-consumption-prediction',
  'name': 'POST /consumption/prediction '
          '(run_consumption_prediction_consumption_prediction_post)',
  'odrl:hasPolicy': {'@id': 'Y29udHJhY3RkZWYtUE9TVC1jb25zdW1wdGlvbi1wcmVkaWN0aW9u:UE9TVC1jb25zdW1wdGlvbi1wcmVkaWN0aW9u:ZTZhMjRmNDEtZjg2ZS00MTA1LWIyOWQtNjhmMjhhMTM0NGM5',
                     '@type': 'odrl:Set',
                     'odrl:obligation': [],
                     'odrl:permission': {'odrl:action': {'odrl:type': 'USE'},
                                         'odrl:constraint': {'odrl:leftOperand': 'hasCredential',
                                                             'odrl:operator': {'@id': 'odrl:isPartOf'},
                                                             'odrl:rightOperand': 'expectedCredential'},
                                         'odrl:target': 'POST-consumption-prediction'},
                     'odrl:prohibition': [],
                     'odrl:target': {'@id': 'POST-consumption-prediction'}}},

[...]
```

If you check the logs of the `consumer` or `provider` connector containers, you will see that they exchange Verifiable Presentations and Verifiable Credentials encoded as JSON Web Tokens (JWT). For example:

```console
$ docker logs provider

[...]

DEBUG 2024-04-04T12:17:43.009342005 Counter-party VP JSON: {"holder":"did:web:gaiax.cticpoc.com:consumer#xhATbcOt4Eha0ZOMdzNOGLqr3ZK7oDMLtjgbVna2UZ8","id":"urn:uuid:d488d603-a0c4-4e9b-89d8-0e64b14af4d7","type":["VerifiablePresentation"],"@context":["https://www.w3.org/2018/credentials/v1"],"verifiableCredential":[{"issuanceDate":"2024-04-04T12:17:01.436519805Z","credentialSubject":{"gx:headquarterAddress":{"gx:countrySubdivisionCode":"ES-AS"},"gx-terms-and-conditions:gaiaxTermsAndConditions":"https://example.com/tac/4c90e4d9cae9453c89ba8d17f45d39db","gx:legalRegistrationNumber":{"id":"https://example.com/lrn/6cc9f04b36aa44b18ccb3230962b9c37"},"schema:description":"This field demonstrates the possibility of using additional ontologies to add fields that are not explicitly included in the Trust Framework specification.","gx:legalAddress":{"gx:countrySubdivisionCode":"ES-AS"},"id":"did:web:gaiax.cticpoc.com:consumer#xhATbcOt4Eha0ZOMdzNOGLqr3ZK7oDMLtjgbVna2UZ8","type":"gx:LegalParticipant","gx:legalName":"Consumer"},"id":"urn:uuid:d32c2977-74d7-42cd-81b7-6519174f23ce","type":["VerifiableCredential","DataCellarCredential"],"@context":["https://www.w3.org/2018/credentials/v1","https://w3id.org/security/suites/jws-2020/v1","https://registry.lab.gaia-x.eu/development/api/trusted-shape-registry/v1/shapes/jsonld/trustframework#","https://schema.org/version/latest/schemaorg-current-https.jsonld"],"issuer":{"id":"did:web:gaiax.cticpoc.com:anchor"},"expirationDate":"2025-04-04T12:17:01.436570430Z"}]}

[...]
```

> [!TIP]
> You can use [jwt.io](https://jwt.io/) to decode the JWT-encoded Verifiable Presentations exchanged between the connectors.
