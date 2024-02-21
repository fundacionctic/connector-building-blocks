from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "NegotiationInitiateRequestDto",
    "connectorId": None,
    "counterPartyAddress": None,
    "consumerId": None,
    "providerId": None,
    "protocol": "dataspace-protocol-http",
    "policy": {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@id": None,
        "@type": "Set",
        "permission": [],
        "prohibition": [],
        "obligation": [],
        "target": None,
    },
}


class ContractNegotiation:
    @classmethod
    def build(
        cls,
        counter_party_connector_id: str,
        counter_party_protocol_url: str,
        consumer_id: str,
        provider_id: str,
        offer_id: str,
        asset_id: str,
    ) -> dict:
        return list_override_merger.merge(
            _TEMPLATE,
            {
                "connectorId": counter_party_connector_id,
                "counterPartyAddress": counter_party_protocol_url,
                "consumerId": consumer_id,
                "providerId": provider_id,
                "policy": {"@id": offer_id, "target": asset_id},
            },
        )
