from typing import Any, Optional

from deepmerge import Merger

list_override_merger = Merger(
    [(list, ["override"]), (dict, ["merge"]), (set, ["union"])],
    ["override"],
    ["override"],
)

EDC_NAMESPACE = "https://w3id.org/edc/v0.0.1/ns/"


def edc_get(d: dict, key: str, default: Optional[Any] = None) -> Any:
    """Get a value from a dict, trying both the short key and the EDC-namespaced key.

    When assets are created via the EDC Management API directly, property keys
    in the JWT data address come back with the full namespace prefix
    (e.g., ``https://w3id.org/edc/v0.0.1/ns/method`` instead of ``method``).
    This helper transparently handles both formats.
    """

    if key in d:
        return d[key]

    namespaced_key = f"{EDC_NAMESPACE}{key}"

    return d.get(namespaced_key, default)


def join_url(*parts):
    return "/".join([part.strip("/") for part in parts])
