from deepmerge import Merger

list_override_merger = Merger(
    [(list, ["override"]), (dict, ["merge"]), (set, ["union"])],
    ["override"],
    ["override"],
)


def join_url(*parts):
    return "/".join([part.strip("/") for part in parts])
