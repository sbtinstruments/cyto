from typing import Any

from ..current_task import instances


class ResultCollection(list[Any]):
    pass


def add_result(result: Any) -> None:
    results = instances().setdefault(ResultCollection())
    results.append(result)
