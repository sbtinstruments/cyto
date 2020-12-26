# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere precense. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# type: ignore[no-untyped-def]
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
from typing import Type

from ..conftest import Argv
from .conftest import Layer, NestedSettings, PartialSettings


def test_set_partial_with_toml(
    fs,
    partial_settings: Type[PartialSettings],
    argv: Argv,
) -> None:
    fs.create_file("/etc/foobar/first.toml", contents="my_int = -55")
    fs.create_file("./second.foobar.toml", contents='my_string = "string with spaces"')
    settings = partial_settings()
    assert settings.my_bool is False
    assert settings.my_int == -55
    assert settings.my_string == "string with spaces"


def test_set_nested_with_toml(
    fs,
    nested_settings: Type[NestedSettings],
    argv: Argv,
) -> None:
    contents = """
        [cake]
        num_candles = 4

        [[cake.layers]]
        name = "ice cream"
        thick = true

        [[cake.layers]]
        name = "meringue"
    """
    fs.create_file("/etc/foobar/a.toml", contents=contents)
    settings = nested_settings()
    assert settings.cake.num_candles == 4
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]


def test_merging(
    fs,
    nested_settings: Type[NestedSettings],
    argv: Argv,
) -> None:
    contents = """
        [cake]
        num_candles = 4

        [[cake.layers]]
        name = "ice cream"
        thick = true

        [[cake.layers]]
        name = "meringue"
    """
    fs.create_file("/etc/foobar/a.toml", contents=contents)
    settings = nested_settings()
    assert settings.cake.num_candles == 4
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]

    # As a general rule, entries in files with higher precedence override the
    # entries in other files. So in case of conflict, the high-precedence entry
    # overrides the lower-precedence entry.
    #
    # There is one exception though: When the conflicting entries are objects.
    # In this case, we merge the objects together.

    # `b.toml` assigns a new `Cake` instance to `cake`.
    contents = """
        [cake]
        num_candles=2
    """
    fs.create_file("/etc/foobar/b.toml", contents=contents)
    settings = nested_settings()
    # As expected, the settings file now reflects the new `Cake` instance
    assert settings.cake.num_candles == 2
    # Note that we didn't specify any layers in the new `Cake` instance.
    # The layers from `a.toml` are still there. This is because we merge
    # the `Cake` instances from `a.toml` and `b.toml` under the hood.
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert len(settings.cake.layers) == 2

    # There is no exception for lists. So, if we specify `layers`, we
    # override any existing entries.
    contents = """
        [cake]

        [[cake.layers]]
        name = "lemon curd"
    """
    fs.create_file("/etc/foobar/c.toml", contents=contents)
    settings = nested_settings()
    # We still see the untouched remnants from `a.toml`
    assert settings.cake.num_candles == 2
    # The layers themselves, however, are gone. The new list instance from
    # `c.toml` overrides any existing entries.
    assert settings.cake.layers == [Layer(name="lemon curd", thick=False)]
