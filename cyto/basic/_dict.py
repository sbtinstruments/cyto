from typing import Any, Dict


def deep_update(dest: Dict[Any, Any], other: Dict[Any, Any]) -> None:
    """Update `dest` with the key/value pairs from `other`.

    Returns `None`. Note that we modify `dest` in place.

    Unlike the built-in `dict.Update`, `deep_update` recurses into sub-dictionaries.
    This effectively "merges" `other` into `dest`.

    Note that we do not recurse into lists. We treat lists like any other
    non-`dict` type and simply override the existing entry in `dest` (if any).
    """
    for key, other_val in other.items():
        # Simple case: `key` is not in `dest`, so we simply add it.
        if key not in dest:
            dest[key] = other_val
            continue
        # Complex case: There is a conflict, so we must "merge" `dest_val`
        # and `other_val`.
        dest_val = dest[key]
        # Given two dicts, we can simply recurse.
        if isinstance(dest_val, dict) and isinstance(other_val, dict):
            deep_update(dest_val, other_val)
        # Any other type combination simply overrides the existing key in `dest`
        else:
            dest[key] = other_val
