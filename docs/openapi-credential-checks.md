# Verifiable Credential Checks in OpenAPI Schemas

By default, all authenticated participants of the data space have access to all _Datasets_ (i.e., HTTP API endpoints) exposed by a connector that uses the OpenAPI extension. However, this is not ideal, as most scenarios will likely require further restriction of access to API endpoints by imposing constraints for specific types of Verifiable Credentials or claims.

Our proposed solution to this requirement is based on providers using [_presentation definitions_](https://identity.foundation/presentation-exchange/spec/v2.0.0/#presentation-definition) to define the proofs that are required. These presentation definitions are included in the OpenAPI schema of the HTTP API exposed to the data space using an [OpenAPI extension](https://swagger.io/specification/). This specific extension key is `x-connector-presentation-definition`.

For example, an OpenAPI path for an API endpoint that utilizes this extension might look like the following:

> [!TIP]
> Note that this is not the complete OpenAPI schema, but rather a specific _path_.

```json
{
  "/consumption/prediction": {
    "post": {
      "tags": [
        "Electricity consumption"
      ],
      "summary": "Run Consumption Prediction",
      "description": "Run the ML model for prediction of electricity consumption for the given time period.",
      "operationId": "run_consumption_prediction_consumption_prediction_post",
      "requestBody": {
        "content": {
          "application/json": {
            "schema": {
              "$ref": "#/components/schemas/ElectricityConsumptionPredictionRequest"
            }
          }
        },
        "required": true
      },
      "responses": {
        "200": {
          "description": "Successful Response",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ElectrictyConsumptionData"
              }
            }
          }
        }
      },
      "x-connector-presentation-definition": {
        "id": "43ea197d-2f3e-41dd-b942-16f8276624f9",
        "input_descriptors": [
          {
            "id": "datacellar-credential",
            "name": "The specific type of VC for Data Cellar",
            "purpose": "This is a simple example of how to declare the types of VCs that the connector expects to allow access to this endpoint.",
            "constraints": {
              "fields": [
                {
                  "path": [
                    "$.type"
                  ],
                  "filter": {
                    "type": "string",
                    "pattern": "DataCellarCredential"
                  }
                }
              ]
            }
          }
        ]
      }
    }
  }
}
```

The OpenAPI connector extension can parse the presentation definition to build policies that attempt to match the pattern of the Verifiable Credentials type indicated by the filter `$.type`. For example, here is a _Dataset_ with such a policy:

> [!TIP]
> Note that the *Datasets* representing the HTTP API endpoints are automatically generated by the OpenAPI connector extension from the OpenAPI schema file of the HTTP API.

```json
{
  "@id": "POST-consumption-prediction",
  "@type": "dcat:Dataset",
  "dcat:distribution": [
    {
      "@type": "dcat:Distribution",
      "dcat:accessService": "31580961-2afc-4ad8-a3b9-b44d5810ced0",
      "dct:format": {
        "@id": "HttpProxy"
      }
    },
    {
      "@type": "dcat:Distribution",
      "dcat:accessService": "31580961-2afc-4ad8-a3b9-b44d5810ced0",
      "dct:format": {
        "@id": "HttpData"
      }
    }
  ],
  "id": "POST-consumption-prediction",
  "name": "POST /consumption/prediction (run_consumption_prediction_consumption_prediction_post)",
  "odrl:hasPolicy": {
    "@id": "Y29udHJhY3RkZWYtUE9TVC1jb25zdW1wdGlvbi1wcmVkaWN0aW9u:UE9TVC1jb25zdW1wdGlvbi1wcmVkaWN0aW9u:NjY0ZTY3YjMtMDI3NC00OGY1LTllMTUtZjU5ZmQzZjRiMzY5",
    "@type": "odrl:Set",
    "odrl:obligation": [],
    "odrl:permission": {
      "odrl:action": {
        "odrl:type": "USE"
      },
      "odrl:constraint": {
        "odrl:leftOperand": "hasVerifiableCredentialType",
        "odrl:operator": {
          "@id": "odrl:isPartOf"
        },
        "odrl:rightOperand": "DataCellarCredential"
      },
      "odrl:target": "POST-consumption-prediction"
    },
    "odrl:prohibition": [],
    "odrl:target": {
      "@id": "POST-consumption-prediction"
    }
  }
}
```

The OpenAPI connector extension implements the logic for the `hasVerifiableCredentialType` constraint, which retrieves the Verifiable Presentation from the counterparty participant claims and validates that the presentation contains at least one Verifiable Credential of the expected type.

In other words, in this case, a consumer who does not present a Verifiable Presentation containing a Verifiable Credential of type `DataCellarCredential` will not be allowed access to the `POST-consumption-prediction` _Dataset_.

> [!WARNING]
> Currently, the extension only supports checking for filters that target `$.type`, meaning we can only check for Verifiable Credential types. Future versions may implement logic for more advanced claim checks.
