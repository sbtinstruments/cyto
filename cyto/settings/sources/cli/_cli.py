from __future__ import annotations

import json
import logging
import sys
from collections.abc import Container, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, Literal, get_args, get_origin

import click
from pydantic import BaseModel, BaseSettings
from pydantic.env_settings import SettingsSourceCallable
from pydantic.fields import ModelField
from pydantic.json import pydantic_encoder
from pydantic.types import Json, JsonWrapper
from pydantic.typing import NoArgAnyCallable
from pydantic.utils import lenient_issubclass

from ....basic import count_leaves
from .._api_models import CliExtras

try:
    from rich_click import RichCommand as Command
except ImportError:
    Command = click.Command  # type: ignore[assignment, misc]

_LOGGER = logging.getLogger(__name__)


def cli_settings_source(
    name: str, *, delimiter: str = ".", internal_delimiter: str = "__"
) -> SettingsSourceCallable:
    """Return settings source based on this process' CLI options."""
    if not internal_delimiter.isidentifier():  # [1]
        raise ValueError(
            f'The internal delimiter "{internal_delimiter}" '
            "is not a valid identifier."
        )

    def _cli_settings_source(settings: BaseSettings) -> dict[str, Any]:
        """Return settings from this process' CLI options.

        Limitations:
        * No support for positional arguments

        Examples:
            "--debug"
            {
                "debug": True
            }

            "--no-debug"
            {
                "debug": False
            }

            "--foo.bar /tmp"
            {
                "foo": {
                    "bar": "/tmp"
                }
            }

        """
        result: dict[str, Any] = {}

        def _set_result(**kwargs: Any) -> None:
            nonlocal result
            # Click provides us with all the user-specified options in `kwargs`.
            # To make the `pydantic.BaseModel` fit into Click's API, we flattened
            # the model hierarchy. Now, we convert `kwargs` back into a nested
            # structure of dicts that we can use as a settings source.
            result = _kwargs_to_settings(kwargs, internal_delimiter)

        params: list[click.Parameter] = list(
            _to_options(settings, delimiter, internal_delimiter)
        )
        command = Command(name=name, callback=_set_result, params=params)
        # Per default, click calls `sys.exit` whenever the command is done.
        # We don't want this behaviour, so we disable it with `standalone_mode=False`.
        status_code: int | None = command.main(standalone_mode=False)
        # If `code` is set, the user asked for help (e.g., via "--help").
        # In this case, we exit the application right away.
        if status_code is not None:
            sys.exit(status_code)

        _LOGGER.debug("Got %d setting(s) from the CLI", count_leaves(result))

        return result

    return _cli_settings_source


def _kwargs_to_settings(
    kwargs: dict[str, Any], internal_delimiter: str
) -> dict[str, Any]:
    """Convert flattened kwargs to a nested dict.

    Examples:
        The kwargs:

        `roast_level: 42`
        `preference__cream_and_sugar: True`

        converts to

        `{ "roast_level": 42, "preference": { "cream_and_sugar": True } }`
    """
    result: dict[str, Any] = {}
    for full_name, value in kwargs.items():
        # Skip unset values. E.g., for unspecified CLI options.
        if value is None:
            continue
        # Split the full name into parts.
        # E.g.: "preference__cream_and_sugar" into ["preference", "cream_and_sugar"]
        parts = full_name.split(internal_delimiter)
        # Create nested dicts corresponding to each of the parts
        dic = result
        for part in parts[:-1]:  # Skip the last part. It will hold the value itself.
            dic = dic.setdefault(part, {})
        # Assign the kwarg value to the innermost dict.
        dic[parts[-1]] = value
    return result


def _to_options(
    model: BaseModel | type[BaseModel],
    delimiter: str,
    internal_delimiter: str,
    *,
    parent_path: tuple[str, ...] = (),
    parent_default: Any = None,
) -> Iterable[click.Option]:
    """Convert `pydantic.BaseModel` to the equivalent `click.Option`s.

    ## Example to explain the implementation

    Let's use an example to explain the code below as we go along.
    A simple model-within-a-model:

        class CoffeePreference(BaseModel):
            cream_and_sugar: bool

        class Coffee(BaseModel):
            roast_level: int
            preference: CoffeePreference

    In our example, there are only three fields in total:
      1. `roast_level` (from the root model)
      2. `preference` (from the root model)
      3. `cream_and_sugar` (from the nested model)
    """

    # We go through all the fields of the model.
    for field in model.__fields__.values():
        # Ensure that `field.name` doesn't contain any of the delimiters.
        # Otherwise, the ambiguity makes it impossible to distinguish
        # between nested models and field names.
        _raise_on_delimiter_conflict(field.name, delimiter)
        _raise_on_internal_delimiter_conflict(field.name, internal_delimiter)

        # `field.name` is either:
        #   1. "roast_level"
        #   2. "preference"
        #   3. "cream_and_sugar".
        #
        # In the command line, we prefer kebab case over snake case.
        #
        # `kebab_name` becomes:
        #   1. "roast-level"
        #   2. "preference"
        #   3. "cream-and-sugar".
        kebab_name = field.name.replace("_", "-")

        # Like before, we ensure that `kebab_name` doesn't cause ambiguities.
        _raise_on_delimiter_conflict(kebab_name, delimiter)
        # Note that we don't have to test the internal delimiter since it can't
        # contain the "-" character (see [1]). We assert instead to catch any
        # errors if the check at [1] changes at some point in time.
        assert internal_delimiter not in kebab_name

        # CLI-specific extras (settings)
        extras = field.field_info.extra.get("cli", CliExtras())
        if not isinstance(extras, CliExtras):
            raise TypeError(
                "The 'cli' field setting must be an instance of 'CliExtras'"
            )

        # Skip the field if the user asked for it. This is useful for types that
        # are impossible/difficult to pass in via the CLI. E.g., a cfunction or
        # a class.
        if extras.exclude:
            continue

        # Resolve the default value for this field
        default = _resolve_default(
            field.name, field.default, field.default_factory, parent_default
        )

        # `field.outer_type_` is the type:
        #   1. `int`
        #   2. `CoffeePreference`
        #   3. `bool`
        #
        # Note that sometimes `outer_type_` isn't a type but an instance from the
        # `typing` module. E.g., a `typing.list[int]` instance. Therefore, we use
        # the `lenient_issubclass` utility function instead of `issubclass`. The
        # latter doesn't accept non-types but the former does (hence the leniency).
        #
        # Note that we do *not* recurse into the model if `force_json` is set. This
        # way, the user can control the level recursion.
        if lenient_issubclass(field.outer_type_, BaseModel) and not extras.force_json:
            # Recurse into nested models. E.g., the `CoffeePreference` model
            # from the `preference` field.
            yield from _to_options(
                field.outer_type_,
                delimiter,
                internal_delimiter,
                parent_path=(*parent_path, kebab_name),
                parent_default=default,
            )
            continue
        # If the field isn't a model itself, we call it a "simple" field.
        # E.g., the `roast_level` and `cream_and_sugar` fields. Note that
        # e.g., `typing.List` and `dict` are also simple fields.
        #
        # We can "clickify" simple fields. That is, convert the field into a
        # `click.Option`.
        #
        # First, we need a so-called parameter declaration for the `click.Option`.
        # A parameter declaration is a set of context-specific names for the option.
        # We generate the parameter declaration from the field.
        param_decls = _ParamDecls.from_field(
            field, kebab_name, delimiter, internal_delimiter, parent_path, extras
        )
        # Then, we "clickify" the field.
        yield _Option.from_field(field, param_decls, default, extras)


def _raise_on_delimiter_conflict(name: str, delimiter: str) -> None:
    if delimiter in name:
        raise ValueError(
            f'The "{name}" field conflicts with the delimiter "{delimiter}".'
        )


def _raise_on_internal_delimiter_conflict(name: str, internal_delimiter: str) -> None:
    if internal_delimiter in name:
        raise ValueError(
            f'The "{name}" field conflicts with the internal '
            f'delimiter "{internal_delimiter}".'
        )


@dataclass(frozen=True)
class _ParamDecls:
    # The identifier used in the callback.
    # E.g.: "preference__cream_and_sugar".
    identifier: str
    # The name given to the option (as seen on the command line).
    # E.g.: "--preference.cream-and-sugar"
    name: str

    def __post_init__(self) -> None:
        assert self.identifier.isidentifier()

    @classmethod
    def from_field(
        cls,
        field: ModelField,
        kebab_name: str,
        delimiter: str,
        internal_delimiter: str,
        parent_path: tuple[str, ...],
        extras: CliExtras,
    ) -> _ParamDecls:
        # We use a delimiter (e.g., ".") to separate the names of nested models.
        #
        # `base_option_name` is:
        #   1. "roast-level"
        #   2. "preference.cream-and-sugar".
        base_option_name = delimiter.join((*parent_path, kebab_name))
        # `click` expects the full option name (with a "--" prefix)
        #
        # `full_option_name` is
        #   1. "--roast-level"
        #   2. "--preference.cream-and-sugar/--preference.no-cream-and-sugar"
        #
        # Note that we automatically add a "disable" option for boolean fields.
        full_option_name = _full_option_name(
            field, kebab_name, base_option_name, delimiter, parent_path, extras
        )
        # `click` requires that the option also has a proper identifier
        # so that we can access the option via keyword argument in the callback.
        # Unfortunately, a name such as "preference.cream-and-sugar" is not
        # a proper identifier due to:
        #  * The delimiter (e.g., ".")
        #  * The "-" character from kebab case
        #
        # Therefore, we replace said chars with:
        #  * The internal delimiter (e.g., "__")
        #  * The "_" character from snake case
        #
        # The resulting string is a proper identifier.
        #
        # In our example, `identifier` is:
        #   1. "roast_level"
        #   2. "preference__cream_and_sugar"
        identifier = base_option_name.replace(delimiter, internal_delimiter).replace(
            "-", "_"
        )
        return cls(identifier, full_option_name)

    def as_tuple(self) -> tuple[str, str]:
        return (self.identifier, self.name)


def _full_option_name(
    field: ModelField,
    kebab_name: str,
    base_option_name: str,
    delimiter: str,
    parent_path: tuple[str, ...],
    extras: CliExtras,
) -> str:
    full_option_name = f"--{base_option_name}"
    # Early out of non-boolean fields
    if field.outer_type_ is not bool:
        return full_option_name
    # The user can specify their own "disable" flag
    if extras.disable_flag is not None:
        # Convert into kebab case
        disable_flag = extras.disable_flag.replace("_", "-")
        # Ensure that the disable name is unambiguous
        _raise_on_delimiter_conflict(disable_flag, delimiter)
    # Fall back to a simple "no-" prefix to the "enable" flag
    else:
        disable_flag = f"no-{kebab_name}"
    full_disable_flag = delimiter.join((*parent_path, disable_flag))
    return full_option_name + f"/--{full_disable_flag}"


class JsonType(click.ParamType):
    """JSON parameter type."""

    name = "json"

    # The `self.fail` call always raises. Pylint doesn't know this and complains
    # about inconsistent return statements.
    def convert(  # pylint: disable=inconsistent-return-statements
        self, value: str, param: click.Parameter | None, ctx: click.Context | None
    ) -> Any:
        """Convert raw JSON string to a dict."""
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            self.fail(
                f"'{value}' is invalid JSON. {str(exc)}",
                param,
                ctx,
            )


JSON_TYPE = JsonType()


class _Option(click.Option):
    """A `click.Option` that knows if the user explicitly specified it.

    This allows us to distinguish between the following states:
      * The option has value because it has a default.
      * The option has value because the user explicitly assigned it one
        even if said value coincides with the default.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "callback" in kwargs:
            raise ValueError(
                'You can\'t specify the "callback" argument.'
                "We reserve it for internal use."
            )
        super().__init__(
            *args,
            **kwargs,
            # We filter out options that the user did not explicitly specify.
            # Otherwise, we may erroneously give the field's default a higher
            # precedence.
            callback=allow_if_specified,
        )
        self.specified = False

    def handle_parse_result(self, ctx: Any, opts: Any, args: Any) -> Any:
        self.specified = self.name in opts
        return super().handle_parse_result(ctx, opts, args)

    @classmethod
    def from_field(
        cls,
        field: ModelField,
        param_decls: _ParamDecls,
        default: Any,
        extras: CliExtras,
    ) -> _Option:
        # Clickify the field's members
        type_ = _clickify_type(field.outer_type_, extras)
        default = _clickify_default(default, field.outer_type_, extras)
        show_default = _get_show_default(default, field.outer_type_)
        multiple = _get_multiple(field.outer_type_, extras)
        # Return an option constructed from the clickified field members
        return cls(
            param_decls.as_tuple(),
            type=type_,
            default=default,
            show_default=show_default,
            multiple=multiple,
            help=field.field_info.description,
        )


SingleClickParamType = type | click.ParamType
ClickParamType = SingleClickParamType | tuple[SingleClickParamType, ...]


def _clickify_type(  # pylint: disable=too-many-return-statements
    type_: type, extras: CliExtras
) -> ClickParamType:
    # Early out if the user explicitly opts to not process the field.
    # Useful for classes that do their own processing (serialization/deserialization).
    if extras.force_unprocessed:
        return click.UNPROCESSED
    # Early out if the user explicitly forces the field type to JSON
    if extras.force_json:
        return JSON_TYPE
    # E.g.: Json, Json[list[str]], etc.
    if lenient_issubclass(type_, (Json, JsonWrapper)):
        # Return `str` since pydantic will parse the JSON in a later step
        return str
    # E.g.: dict, dict[str, Any], OrderedDict, etc.
    if _is_mapping(type_):
        return JSON_TYPE
    # E.g.: list, FrozenSet[int], tuple[int, ...], etc.
    if _is_container(type_):
        return _clickify_container_args(type_)
    # `enum.Enum`
    if lenient_issubclass(type_, Enum):
        return _clickify_enum(type_)
    # `typing.Literal`
    if _is_literal(type_):
        return _clickify_literal(type_)
    # click does not support `datetime.timedelta`. We pass it on unprocessed.
    if lenient_issubclass(type_, timedelta):
        return click.UNPROCESSED
    # E.g.: int, str, float, etc.
    return type_


def _clickify_default(
    default: Any,
    type_: type,
    extras: CliExtras,
) -> Any:
    # Pydantic uses both `None` and `Ellipsis` to denote "no default value".
    # Click only understands `None`, so we return that.
    if default in (None, Ellipsis):
        return None
    # Early out if the user explicitly opts to not process the field
    if extras.force_unprocessed:
        return default
    # Early out if the user explicitly forces the field type to JSON
    if extras.force_json or _is_mapping(type_):
        return json.dumps(default, default=pydantic_encoder)
    if _is_container(type_):
        return _clickify_container_default(default)
    if isinstance(default, Enum):
        return default.value
    return default


def _get_show_default(default: Any, type_: type) -> bool | str:
    # click's help message for an empty container is "[default: ]". This can
    # confuse the user user. Therefore, we explicitly set the `show_default`
    # to, e.g., "empty list". In turn, click displays this as
    # "[default: (empty list)]". Note that click adds the parentheses.
    if _is_container(type_) and not default:
        name = _type_name(type_)
        return f"empty {name}"
    # For non-containers, we always show the default. We simply return `True` so
    # that click automatically figures out a proper default text.
    return True


def _get_multiple(type_: type, extras: CliExtras) -> bool:
    # Early out if the user explicitly opts to not process the field.
    if extras.force_unprocessed:
        return False
    # Early out if the user explicitly forces the field type to JSON
    if extras.force_json:
        return False
    # Early out for mappings. E.g., dict.
    if _is_mapping(type_):
        return False
    # For containers, we allow multiple arguments. This way, the user
    # can specify an option multiple times and click gathers all values
    # into a single container. E.g.:
    #   $ python app.py --lucky-numbers 2 --lucky-numbers 7
    # becomes
    #   `{ "lucky_numbers": [2, 7] }`.
    if _is_container(type_):
        args = _clickify_container_args(type_)
        # A non-composite type has a single argument.
        # E.g., `list[int]`.
        # A composite type has a tuple of arguments.
        # E.g., `tuple[str, int, int]`.
        composite = isinstance(args, tuple)
        # We only allow the user to specify multiple values for non-composite types.
        # E.g., for `list`, `tuple[str, ...]`, `FrozenSet[int]`, etc.
        return not composite
    return False


def _is_mapping(type_: type) -> bool:
    # Early out for standard containers. E.g., dict, OrderedDict
    if lenient_issubclass(type_, Mapping):
        return True
    origin = get_origin(type_)
    # Early out for non-typing objects
    if origin is None:
        return False
    return lenient_issubclass(origin, Mapping)


def _is_container(type_: type) -> bool:
    # Early out for `str`. While `str` is technically a container, it's easier to
    # not consider it one in the context of command line interfaces.
    if type_ is str:
        return False
    # Early out for standard containers. E.g.: list, tuple, range
    if lenient_issubclass(type_, Container):
        return True
    origin = get_origin(type_)
    # Early out for non-typing objects
    if origin is None:
        return False
    return lenient_issubclass(origin, Container)


def _is_literal(type_: type) -> bool:
    return get_origin(type_) is Literal


def _clickify_literal(literal: type) -> ClickParamType:
    return click.Choice(get_args(literal))


def _clickify_enum(enum: type[Enum]) -> ClickParamType:
    return click.Choice(tuple(str(value.value) for value in enum.__members__.values()))


def _clickify_container_args(
    type_: type,
) -> ClickParamType:
    assert _is_container(type_)
    args: tuple[Any, ...] = get_args(type_)
    # Early out for untyped containers such as `tuple`, `list[Any]`, `frozenset`, etc.
    if len(args) == 0:
        # When we don't know the type, we choose `str`. It's tempting to choose `None`
        # but that invokes click's type-guessing logic. We don't want to do that since
        # it often incorrectly guesses that we want a composite type when we don't. [2]
        return str
    # Early out for homogeneous containers (contains items of a single type)
    if len(args) == 1:
        return _clickify_arg(args[0])
    # Early out for homogeneous tuples of indefinite length. E.g., `tuple[int, ...]`.
    if len(args) == 2 and args[1] is Ellipsis:
        return _clickify_arg(args[0])
    # Last case is fixed-length containers (contains a fixed number of items of a
    # given type). E.g., `tuple[str, int, int]`.
    return tuple(_clickify_args(args))


def _clickify_args(
    args: tuple[type, ...],
) -> Iterable[SingleClickParamType]:
    return (_clickify_arg(arg) for arg in args)


def _clickify_arg(arg: type) -> SingleClickParamType:
    # When we don't know the type, we choose `str` (see [2])
    if arg is Any:
        return str
    # For containers and nested models, we use JSON
    if _is_container(arg) or issubclass(arg, BaseModel):
        return JSON_TYPE
    return arg


def _clickify_container_default(default: Any) -> tuple[Any, ...] | None:
    assert issubclass(type(default), Sequence)
    return tuple(v.json() if isinstance(v, BaseModel) else v for v in default)


def _type_name(type_: type) -> str:
    origin: type | None = get_origin(type_)
    if origin is None:
        return type_.__name__
    return origin.__name__


def _resolve_default(
    field_name: str,
    default: Any,
    default_factory: NoArgAnyCallable | None,
    parent_default: Any | None,
) -> Any:
    """Resolve the default value (if any) for the field.

    The use of this function allows scenarios such as:

        class Engine(BaseModel):
            power: float          # No default value!
            gasoline_left: float  # No default value!

        class Car(BaseModel):
            engine: Engine = Engine(power=42.8, gasoline_left=1e3)

    In this case, the CLI finds the default values for `power` and `gasoline_left`
    through the `Car`'s default value for `engine`.

    In practice, you may also want to do something like:

        class Car(BaseModel):
            engine: Engine = Field(
                default_factory=lambda: Engine(power=42.8, gasoline_left=1e3)
            )

    This also works since the CLI calls `default_factory` to get the default value.
    With that in mind, ensure that your `default_factory`s are compute/memory efficient
    since we'll call `default_factory` of *every* field that has it.
    """
    # Call `default_factory` (if provided) to create a value for `default`.
    if default_factory is not None and default is None:
        # `default_factory` may fail for various reasons. We suppress that here.
        # It's just a default value anynow.
        with suppress(Exception):
            return default_factory()
    # Use the parent's default value to find the default value of the current field
    if parent_default is not None and default is None:
        try:
            # In the `Car` example from the docsting, this call is something like:
            #
            #     > parent_default = Engine(power=42.8, gasoline_left=1e3)
            #     > return getattr(parent_default, "power")
            #
            # Same thing for the `gasoline_left` field.
            return getattr(parent_default, field_name)
        except AttributeError:
            pass
    return default


def allow_if_specified(_: click.Context, param: click.Parameter, value: Any) -> Any:
    """Only allow options that the user explicitly specified."""
    if isinstance(param, _Option):
        return value if param.specified else None
    return value
