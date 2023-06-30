from datetime import datetime
from typing import Any

from pydantic import BaseModel, Extra

from ....model import FrozenModel
from ..current_task import instances


class ResultCollection(list[ResultEntry]):
    pass


def add_result(result: Any) -> None:
    results = instances().setdefault(ResultCollection())
    results.append(result)
