# pylint: disable=missing-function-docstring,missing-class-docstring

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# type: ignore[no-untyped-def]
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
from typing import List, Type

import pytest
from pydantic import BaseModel, BaseSettings, ValidationError

from cyto.settings import autofill


class Layer(BaseModel):
    name: str
    thick: bool = False


class Cake(BaseModel):
    layers: List[Layer]
    num_candles: int = 9


class DefaultSettings(BaseSettings):
    my_bool: bool = False
    my_int: int = 42
    my_string: str = "Hello test suite"


class PartialSettings(BaseSettings):
    my_bool: bool = False
    my_int: int
    my_string: str


class NestedSettings(BaseSettings):
    store_is_open: bool = True
    cake: Cake = Cake(
        layers=[
            Layer(name="brownie", thick=True),
            Layer(name="cream"),
            Layer(name="glaze"),
        ]
    )


@pytest.fixture
def default_settings() -> Type[DefaultSettings]:
    return autofill(name="foobar")(DefaultSettings)


@pytest.fixture
def partial_settings() -> Type[PartialSettings]:
    return autofill(name="foobar")(PartialSettings)


@pytest.fixture
def nested_settings() -> Type[NestedSettings]:
    return autofill(name="foobar")(NestedSettings)


def test_defaults(default_settings: Type[DefaultSettings]) -> None:
    settings = default_settings()
    assert settings.my_bool is False
    assert settings.my_int == 42
    assert settings.my_string == "Hello test suite"


def test_missing(partial_settings: Type[PartialSettings]) -> None:
    with pytest.raises(ValidationError) as exc_info:
        partial_settings()
    assert exc_info.value.errors() == [
        {"loc": ("my_int",), "msg": "field required", "type": "value_error.missing"},
        {"loc": ("my_string",), "msg": "field required", "type": "value_error.missing"},
    ]


def test_set_partial_with_kwargs(partial_settings: Type[PartialSettings]) -> None:
    settings = partial_settings(my_int=44, my_string="string with spaces")
    assert settings.my_bool is False
    assert settings.my_int == 44
    assert settings.my_string == "string with spaces"


def test_set_partial_with_env(
    monkeypatch, partial_settings: Type[PartialSettings]
) -> None:
    monkeypatch.setenv("foobar_my_int", "99")
    monkeypatch.setenv("foobar_my_string", "string with spaces")
    settings = partial_settings()
    assert settings.my_bool is False
    assert settings.my_int == 99
    assert settings.my_string == "string with spaces"


def test_set_partial_with_toml(fs, partial_settings: Type[PartialSettings]) -> None:
    fs.create_file("/etc/foobar/first.toml", contents="my_int = -55")
    fs.create_file("./second.foobar.toml", contents='my_string = "string with spaces"')
    settings = partial_settings()
    assert settings.my_bool is False
    assert settings.my_int == -55
    assert settings.my_string == "string with spaces"


def test_set_nested_with_kwargs(nested_settings: Type[NestedSettings]) -> None:
    settings = nested_settings(
        cake={
            "layers": [
                {"name": "ice cream", "thick": True},
                {"name": "meringue"},
            ]
        }
    )
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert settings.cake.num_candles == 9


def test_set_nested_with_env(
    monkeypatch, nested_settings: Type[NestedSettings]
) -> None:
    value = """
    {
        "layers": [
            {"name": "ice cream", "thick": true},
            {"name": "meringue"}
        ]
    }
    """
    monkeypatch.setenv("foobar_cake", value)
    settings = nested_settings()
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert settings.cake.num_candles == 9


def test_set_nested_with_toml(fs, nested_settings: Type[NestedSettings]) -> None:
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
    # Still, the layers from `a.toml` are still there. This is because
    # we merge the `Cake` instances from `a.toml` and `b.toml` under the hood.
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


def test_etc_precedence(fs, default_settings: Type[DefaultSettings]) -> None:
    fs.create_file("/etc/foobar/0.toml", contents="my_int = 0")
    fs.create_file("/etc/foobar/1.toml", contents="my_int = 1")
    fs.create_file("/etc/foobar/2.toml", contents="my_int = 2")
    settings = default_settings()
    assert settings.my_int == 2
    # Remove a file to make the other files take precedence
    fs.remove_object("/etc/foobar/2.toml")
    settings = default_settings()
    assert settings.my_int == 1
    # Remove all files to go back to the default
    fs.remove_object("/etc/foobar/1.toml")
    fs.remove_object("/etc/foobar/0.toml")
    settings = default_settings()
    assert settings.my_int == 42


def test_etc_vs_cwd_precedence(fs, default_settings: Type[DefaultSettings]) -> None:
    fs.create_file("/etc/foobar/a.toml", contents="my_int = 1")
    fs.create_file("./a.foobar.toml", contents="my_int = 2")
    settings = default_settings()
    assert settings.my_int == 2


def test_cwd_vs_env_precedence(
    fs, monkeypatch, default_settings: Type[DefaultSettings]
) -> None:
    fs.create_file("./a.foobar.toml", contents="my_int = 2")
    monkeypatch.setenv("foobar_my_int", "3")
    settings = default_settings()
    assert settings.my_int == 3


def test_env_vs_kwarg_precedence(
    monkeypatch, default_settings: Type[DefaultSettings]
) -> None:
    monkeypatch.setenv("foobar_my_int", "3")
    settings = default_settings(my_int=4)
    assert settings.my_int == 4
