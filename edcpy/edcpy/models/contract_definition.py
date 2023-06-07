import uuid

from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": None,
    "accessPolicyId": None,
    "contractPolicyId": None,
    "assetsSelector": [],
}


class ContractDefinition:
    @classmethod
    def build(
        cls,
        policy_definition_id: str,
        uid: str = None,
    ) -> dict:
        uid = uid if uid is not None else "contract-def-{}".format(uuid.uuid4())

        return list_override_merger.merge(
            _TEMPLATE,
            {
                "@id": uid,
                "accessPolicyId": policy_definition_id,
                "contractPolicyId": policy_definition_id,
            },
        )
