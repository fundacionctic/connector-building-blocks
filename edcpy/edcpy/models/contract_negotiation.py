from typing import Any, Dict

from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "ContractRequest",
    "counterPartyAddress": None,
    "protocol": "dataspace-protocol-http",
    "policy": {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@id": None,
        "@type": "Offer",
        "assigner": None,
        "target": None,
    },
}


class ContractNegotiation:
    @classmethod
    def build(
        cls,
        counter_party_connector_id: str,
        counter_party_protocol_url: str,
        asset_id: str,
        policy: Dict[str, Any],
    ) -> dict:
        merged_policy = list_override_merger.merge(
            policy,
            {"assigner": counter_party_connector_id, "target": asset_id},
        )

        return list_override_merger.merge(
            _TEMPLATE,
            {
                "counterPartyAddress": counter_party_protocol_url,
                "policy": merged_policy,
            },
        )
