from collections.abc import Mapping
from typing import Any


def count_leaves(nested_dict: Mapping[str, Any]) -> int:
    """Count the number of "leaf" elements in the given mapping.

    This function recursively explores the given mapping, counting the
    number of non-mapping items ("leaves") it contains.
    """
    count = 0
    for value in nested_dict.values():
        if isinstance(value, Mapping):
            count += count_leaves(value)
        else:
            count += 1
    return count
