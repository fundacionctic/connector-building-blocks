from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "TransferRequestDto",
    "connectorId": None,
    "counterPartyAddress": None,
    "contractId": None,
    "assetId": None,
    "protocol": "dataspace-protocol-http",
    "dataDestination": {},
}


class TransferProcess:
    @classmethod
    def build_for_provider_http_push(
        cls,
        counter_party_connector_id: str,
        counter_party_protocol_url: str,
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
                "connectorId": counter_party_connector_id,
                "counterPartyAddress": counter_party_protocol_url,
                "contractId": contract_agreement_id,
                "assetId": asset_id,
                "dataDestination": {
                    "type": "HttpData",
                    "baseUrl": sink_base_url,
                    "path": sink_path,
                    "method": sink_method,
                    "contentType": sink_content_type,
                },
            },
        )

    @classmethod
    def build_for_consumer_http_pull(
        cls,
        counter_party_connector_id: str,
        counter_party_protocol_url: str,
        contract_agreement_id: str,
        asset_id: str,
    ):
        return list_override_merger.merge(
            _TEMPLATE,
            {
                "connectorId": counter_party_connector_id,
                "counterPartyAddress": counter_party_protocol_url,
                "contractId": contract_agreement_id,
                "assetId": asset_id,
                "dataDestination": {
                    "type": "HttpProxy",
                },
            },
        )
