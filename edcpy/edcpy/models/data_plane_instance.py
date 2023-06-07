import uuid

from edcpy.utils import join_url, list_override_merger

_TEMPLATE = {
    "edctype": "dataspaceconnector:dataplaneinstance",
    "id": None,
    "url": None,
    "allowedSourceTypes": ["HttpData"],
    "allowedDestTypes": ["HttpProxy", "HttpData"],
    "properties": {"publicApiUrl": None},
}


class DataPlaneInstance:
    @classmethod
    def build(
        cls,
        control_url: str,
        public_api_url: str,
        uid: str = None,
    ) -> dict:
        uid = uid if uid is not None else "dplane-{}".format(uuid.uuid4())

        return list_override_merger.merge(
            _TEMPLATE,
            {
                "id": uid,
                "url": join_url(control_url, "transfer"),
                "properties": {"publicApiUrl": public_api_url},
            },
        )
