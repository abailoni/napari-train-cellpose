from copy import deepcopy

import yaml


class OverrideDict(dict):
    """class to allow overriding of whole dictionaries in recursive_update"""

    def after_override(self):
        return dict(self)


def override_constructor(loader, node):
    if isinstance(node, yaml.MappingNode):
        return OverrideDict(loader.construct_mapping(node))
    else:
        raise NotImplementedError("Node: " + str(type(node)))


yaml.add_constructor("!Override", override_constructor)


class KeyDeleter:
    """class to allow deletion of dictionarly keys in recursive_update"""


def key_delete_constructor(loader, node):
    assert node.value == "", f"{node.value}"
    return KeyDeleter()


yaml.add_constructor("!Del", key_delete_constructor)


def override_constructor(loader, node):
    if isinstance(node, yaml.MappingNode):
        return OverrideDict(loader.construct_mapping(node))
    else:
        raise NotImplementedError("Node: " + str(type(node)))


def _recursive_update_inplace(d1, d2):
    if isinstance(d2, OverrideDict):
        # if requested, just override the whole dict d1
        return d2.after_override()
    for key, value in d2.items():
        if isinstance(value, KeyDeleter) or value == "KeyDeleter":
            # delete the key in d1 if requested
            if key in d1:
                del d1[key]
        elif (
            key in d1 and isinstance(d1[key], dict) and isinstance(value, dict)
        ):
            # if the key is present in both dicts, and both values are
            # dicts, update recursively
            d1[key] = _recursive_update_inplace(d1[key], value)
        else:
            # otherwise, just assign the value
            d1[key] = value
    return d1


def recursive_update(d1, d2):
    """
    Update d1 with the data from d2 recursively
    :param d1: dict
    :param d2: dict
    :return: dict
    """
    # make sure there are no side effects
    d1 = deepcopy(d1)
    d2 = deepcopy(d2)
    return _recursive_update_inplace(d1, d2)
