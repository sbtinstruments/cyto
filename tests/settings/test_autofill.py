# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere presence. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# mypy: disable-error-code=no-untyped-def
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
import pytest
from pydantic import ValidationError

from .conftest import DefaultSettings, Layer, NestedSettings, PartialSettings


def test_defaults(
    default_settings: type[DefaultSettings],
) -> None:
    settings = default_settings()
    assert settings.my_bool is False
    assert settings.my_int == 42
    assert settings.my_string == "Hello test suite"


def test_missing(
    partial_settings: type[PartialSettings],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        partial_settings()
    assert exc_info.value.errors() == [
        {"loc": ("my_int",), "msg": "field required", "type": "value_error.missing"},
        {"loc": ("my_string",), "msg": "field required", "type": "value_error.missing"},
    ]


def test_set_partial_with_kwargs(
    partial_settings: type[PartialSettings],
) -> None:
    settings = partial_settings(my_int=44, my_string="string with spaces")
    assert settings.my_bool is False
    assert settings.my_int == 44
    assert settings.my_string == "string with spaces"


def test_set_partial_with_env(
    monkeypatch,
    partial_settings: type[PartialSettings],
) -> None:
    monkeypatch.setenv("foobar_my_int", "99")
    monkeypatch.setenv("foobar_my_string", "string with spaces")
    settings = partial_settings()
    assert settings.my_bool is False
    assert settings.my_int == 99
    assert settings.my_string == "string with spaces"


def test_set_nested_with_kwargs(
    nested_settings: type[NestedSettings],
) -> None:
    settings = nested_settings(
        cake={
            "layers": [
                {"name": "ice cream", "thick": True},
                {"name": "meringue"},
            ],
            "price": 12,
        }
    )
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert settings.cake.num_candles == 9


def test_set_nested_with_env(
    monkeypatch,
    nested_settings: type[NestedSettings],
) -> None:
    value = """
    {
        "layers": [
            {"name": "ice cream", "thick": true},
            {"name": "meringue"}
        ],
        "price": 12
    }
    """
    monkeypatch.setenv("foobar_cake", value)
    settings = nested_settings()
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert settings.cake.num_candles == 9
