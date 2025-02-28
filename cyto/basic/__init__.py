"""Everything here depends solely on the python standard library."""

from ._async_iterable import distinct_until_changed as distinct_until_changed
from ._async_iterable import start_with as start_with
from ._context import AsyncContextStack as AsyncContextStack
from ._context import ContextStack as ContextStack
from ._context import ReentrantAsyncContextStack as ReentrantAsyncContextStack
from ._context import ReentrantContextStack as ReentrantContextStack
from ._dict import deep_update as deep_update
from ._get_app_name import get_app_name as get_app_name
from ._get_app_name import get_root_app_name as get_root_app_name
from ._get_app_name import set_root_app_name as set_root_app_name
from ._mapping import count_leaves as count_leaves
