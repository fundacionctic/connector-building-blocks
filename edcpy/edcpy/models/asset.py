import uuid

from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
    "asset": {
        "@id": None,
        "properties": {"name": None, "contenttype": None},
    },
    "dataAddress": {
        "@type": "DataAddress",
        "type": "HttpData",
        "properties": {
            "type": "HttpData",
            "name": None,
            "baseUrl": None,
            "path": None,
            "method": None,
        },
    },
}


class Asset:
    @classmethod
    def build_http_data(
        cls,
        source_base_url: str,
        source_path: str,
        source_method: str = "GET",
        source_content_type: str = "application/json",
        uid: str = None,
    ) -> dict:
        uid = uid if uid is not None else "asset-{}".format(uuid.uuid4())

        return list_override_merger.merge(
            _TEMPLATE,
            {
                "asset": {
                    "@id": uid,
                    "properties": {
                        "name": f"Name of asset {uid}",
                        "contenttype": source_content_type,
                    },
                },
                "dataAddress": {
                    "properties": {
                        "name": f"Data address of asset {uid}",
                        "baseUrl": source_base_url,
                        "path": source_path,
                        "method": source_method,
                    }
                },
            },
        )
