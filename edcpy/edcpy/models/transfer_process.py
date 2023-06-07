from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "TransferRequestDto",
    "dataDestination": {},
    "protocol": "dataspace-protocol-http",
    "connectorId": None,
    "connectorAddress": None,
    "contractId": None,
    "assetId": None,
    "privateProperties": {},
    "managedResources": False,
}


class TransferProcess:
    @classmethod
    def build_for_provider_http_push(
        cls,
        connector_id: str,
        connector_ids_url: str,
        contract_agreement_id: str,
        asset_id: str,
        sink_base_url: str,
        sink_path: str,
        sink_method: str = "POST",
        sink_content_type: str = "application/json",
    ):
        return list_override_merger.merge(
            _TEMPLATE,
            {
                "dataDestination": {
                    "@type": "DataAddress",
                    "type": "HttpData",
                    "properties": {
                        "baseUrl": sink_base_url,
                        "path": sink_path,
                        "method": sink_method,
                        "contentType": sink_content_type,
                    },
                },
                "connectorId": connector_id,
                "connectorAddress": connector_ids_url,
                "contractId": contract_agreement_id,
                "assetId": asset_id,
            },
        )

    @classmethod
    def build_for_consumer_http_pull(
        cls,
        connector_id: str,
        connector_ids_url: str,
        contract_agreement_id: str,
        asset_id: str,
    ):
        return list_override_merger.merge(
            _TEMPLATE,
            {
                "dataDestination": {"@type": "DataAddress", "type": "HttpProxy"},
                "connectorId": connector_id,
                "connectorAddress": connector_ids_url,
                "contractId": contract_agreement_id,
                "assetId": asset_id,
            },
        )
