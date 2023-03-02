import sys
from dataclasses import dataclass
from inspect import Parameter
from typing import Any, get_args

from pydantic import parse_obj_as


@dataclass(frozen=True)
class Param:
    """Runtime parameter given through CLI or by other means."""


def parameter_factory(param: Parameter) -> Any:
    anno_args = get_args(param.annotation)
    param_anno_args = (
        anno_arg for anno_arg in anno_args if isinstance(anno_arg, Param)
    )
    # Early out if this factory doesn't apply
    try:
        _ = next(iter(param_anno_args))
    except StopIteration as exc:
        raise ValueError from exc

    prefix = "--" + param.name.replace("_", "-") + "="
    arg_type = anno_args[0]  # Type is always first
    try:
        arg = next(arg for arg in sys.argv if arg.startswith(prefix))
        value = arg.removeprefix(prefix)
    except StopIteration:
        value = param.default

    return parse_obj_as(arg_type, value)
