import sys
from collections import defaultdict
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Tuple

import click
from pydantic import BaseModel, BaseSettings
from pydantic.env_settings import SettingsSourceCallable


def cli_settings(name: str) -> SettingsSourceCallable:
    """Return settings source based on this process' CLI options."""

    def _cli_settings(settings: BaseSettings) -> Dict[str, Any]:
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
        result: Dict[str, Any] = {}

        def _set_result(**kwargs: Any) -> None:
            nonlocal result
            # Click provides us with all the user-specified options in `kwargs`.
            # To make the `pydantic.BaseModel` fit into Click's API, we flattened
            # the model hierarchy. Now, we convert `kwargs` back into a nested
            # structure of dicts that we can use as a settings source.
            result = _kwargs_to_settings(kwargs)

        params: List[click.Parameter] = list(_to_options(settings))
        command = click.Command(name=name, callback=_set_result, params=params)
        # Per default, click calls `sys.exit` whenever the command is done.
        # We don't want this behaviour, so we disable it with `standalone_mode=False`.
        code: Optional[int] = command.main(standalone_mode=False)
        # If `code` is set, the user asked for help (e.g., via "--help").
        # In this case, we exit the application right away.
        if code is not None:
            sys.exit(code)

        return result

    return _cli_settings


def _kwargs_to_settings(
    kwargs: Dict[str, Any], delimiter: str = "__"
) -> Dict[str, Any]:
    """Convert flattened kwargs to a nested dict.

    Examples:
        The kwargs:

        `roast_level: 42`
        `preference__cream_and_sugar: True`

        converts to

        `{ "roast_level": 42, "preference": { "cream_and_sugar": True } }`
    """
    result: DefaultDict[str, Any] = defaultdict(dict)
    for full_name, value in kwargs.items():
        # Skip unset values. E.g., for unspecified CLI options.
        if value is None:
            continue
        # Split the full name into parts.
        # E.g.: "preference__cream_and_sugar" into ["preference", "cream_and_sugar"]
        parts = full_name.split(delimiter)
        # Create nested dicts corresponding to each of the parts
        dic = result
        for part in parts[:-1]:  # Skip the last part. It will hold the value itself.
            dic = dic[part]
        # Assign the kwarg value to the innermost dict.
        dic[parts[-1]] = value
    return dict(result)


def _to_options(
    model: BaseModel, *, parent_path: Tuple[str, ...] = tuple()
) -> Iterable[click.Option]:
    """Convert `pydantic.BaseModel` to the equivalent `click.Option`s."""
    # Let's use an example to explain the code below as we go along.
    # A simple model-within-a-model:
    #
    #     class CoffeePreference(BaseModel):
    #         cream_and_sugar: bool
    #
    #     class Coffee(BaseModel):
    #         roast_level: int
    #         preference: CoffeePreference
    #
    # In our example, there are only three fields in total:
    #   1. `roast_level` (from the root model)
    #   2. `preference` (from the root model)
    #   3. `cream_and_sugar` (from the nested model)

    # We go through all the fields of the model.
    for field in model.__fields__.values():
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
        if issubclass(field.type_, BaseModel):
            # Recurse into nested models. E.g., the `CoffeePreference` model
            # from the `preference` field.
            yield from _to_options(field.type_, parent_path=parent_path + (kebab_name,))
            continue
        # We use a period to separate the names of nested models.
        #
        # `base_option_name` is:
        #   1. "roast-level"
        #   2. "preference.cream-and-sugar".
        base_option_name = ".".join(parent_path + (kebab_name,))
        # `click` expects the full option name (with a "--" prefix)
        #
        # `full_option_name` is
        #   1. "--roast-level"
        #   2. "--preference.cream-and-sugar/--preference.no-cream-and-sugar"
        #
        # Note that we automatically add a "disable" option for boolean fields.
        full_option_name = f"--{base_option_name}"
        if field.type_ is bool:
            try:
                # Allow the user to specify their own name for the "disable" option.
                disable_name = field.field_info.extra["disable_name"]
            except KeyError:
                # Fall back to a simply "no-" prefix to the "enable" option.
                disable_name = f"no-{kebab_name}"
            full_cli_disable_name = ".".join(parent_path + (disable_name,))
            full_option_name += f"/--{full_cli_disable_name}"
        # `click` requires that the option also has a proper identifier
        # so that we can access the option via keyword argument in the callback.
        # Unfortunately, a name such as "preference.cream-and-sugar" is not
        # a proper identifier due to the "." and "-" characters.
        # Fortunately, if we replace said chars with underscores, the resulting
        # string is a proper identifier.
        #
        # `identifier_name` is
        #   1. "roast_level"
        #   2. "preference__cream_and_sugar"
        identifier_name = base_option_name.replace(".", "__").replace("-", "_")
        # `param_decls` consists of two strings: The first is the identifier name that
        # `click` use in the callback function and the second is the option name that we
        # see on the command line.
        param_decls = [identifier_name, full_option_name]
        # pydantic uses `Ellipsis` to denote "no default value". We convert
        # this to `None` so that click understands it.
        default = field.default if field.default is not Ellipsis else None
        # Finally, we create the `click.Option` instance itself.
        yield _Option(
            param_decls,
            default=default,
            show_default=True,
            type=field.type_,
            help=field.field_info.description,
            # We filter out options that the user did not explicitly specify.
            # Otherwise, we may erroneously give the field's default a higher
            # precedence.
            callback=allow_if_specified,
        )


class _Option(click.Option):
    """A `click.Option` that knows if the user explicitly specified it.

    This allows us to distinguish between the following states:
      * The option has value because it has a default.
      * The option has value because the user explicitly assigned it one
        even if said value coincides with the default.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.specified = False

    def handle_parse_result(self, ctx: Any, opts: Any, args: Any) -> Any:
        self.specified = self.name in opts
        return super().handle_parse_result(ctx, opts, args)


def allow_if_specified(_: click.Context, param: click.Parameter, value: Any) -> Any:
    """Only allow options that the user explicitly specified."""
    if isinstance(param, _Option):
        return value if param.specified else None
    return value
