import uuid

from edcpy.utils import list_override_merger


_TEMPLATE = {
    "@context": {
        "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
        "odrl": "http://www.w3.org/ns/odrl/2/",
    },
    "@id": None,
    "policy": {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Set",
        "permission": [],
        "prohibition": [],
        "obligation": [],
    },
}


class PolicyDefinition:
    @classmethod
    def build(
        cls,
        uid: str = None,
    ) -> dict:
        uid = uid if uid is not None else f"policy-def-{uuid.uuid4()}"

        return list_override_merger.merge(
            _TEMPLATE,
            {"@id": uid},
        )
