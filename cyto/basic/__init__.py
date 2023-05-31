"""Everything here depends solely on the python standard library."""
from ._async_iterable import distinct_until_changed, start_with
from ._context import AsyncContextStack
from ._dict import deep_update
from ._get_app_name import get_app_name

__all__ = (
    "distinct_until_changed",
    "start_with",
    "AsyncContextStack",
    "deep_update",
    "get_app_name",
)
