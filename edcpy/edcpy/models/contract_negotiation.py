from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "NegotiationInitiateRequestDto",
    "connectorId": None,
    "consumerId": None,
    "providerId": None,
    "connectorAddress": None,
    "protocol": "dataspace-protocol-http",
    "offer": {
        "offerId": None,
        "assetId": None,
        "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@id": None,
            "@type": "Set",
            "permission": [],
            "prohibition": [],
            "obligation": [],
            "target": None,
        },
    },
}


class ContractNegotiation:
    @classmethod
    def build(
        cls,
        connector_id: str,
        connector_ids_url: str,
        consumer_id: str,
        provider_id: str,
        offer_id: str,
        asset_id: str,
    ) -> dict:
        return list_override_merger.merge(
            _TEMPLATE,
            {
                "connectorId": connector_id,
                "connectorAddress": connector_ids_url,
                "consumerId": consumer_id,
                "providerId": provider_id,
                "offer": {
                    "offerId": offer_id,
                    "assetId": asset_id,
                    "policy": {
                        "@id": offer_id,
                        "target": asset_id,
                    },
                },
            },
        )
