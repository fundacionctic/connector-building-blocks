import uuid

from edcpy.utils import list_override_merger

_TEMPLATE = {
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": None,
    "properties": {"name": None, "contenttype": None},
    "dataAddress": {
        "type": "HttpData",
        "name": None,
        "baseUrl": None,
        "proxyPath": None,
    },
}


class Asset:
    @classmethod
    def build_http_data(
        cls,
        source_base_url: str,
        source_method: str = "GET",
        source_content_type: str = "application/json",
        uid: str = None,
        proxy_body: bool = True,
        proxy_path: bool = True,
        proxy_query_params: bool = True,
        proxy_method: bool = True,
    ) -> dict:
        uid = uid if uid is not None else f"asset-{uuid.uuid4()}"

        data_address_props = {
            "name": f"Data address of asset {uid}",
            "baseUrl": source_base_url,
            "method": source_method,
        }

        if proxy_body:
            data_address_props["proxyBody"] = "true"

        if proxy_path:
            data_address_props["proxyPath"] = "true"

        if proxy_query_params:
            data_address_props["proxyQueryParams"] = "true"

        if proxy_method:
            data_address_props["proxyMethod"] = "true"

        return list_override_merger.merge(
            _TEMPLATE,
            {
                "@id": uid,
                "properties": {
                    "name": f"Name of asset {uid}",
                    "contenttype": source_content_type,
                },
                "dataAddress": data_address_props,
            },
        )
