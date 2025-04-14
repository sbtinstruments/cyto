import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch  # noqa: PT013

from .conftest import DefaultSettings, Layer, NestedSettings, PartialSettings


def test_defaults() -> None:
    settings = DefaultSettings()
    assert settings.my_bool is False
    assert settings.my_int == 42
    assert settings.my_string == "Hello test suite"


def test_missing() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PartialSettings()
    assert exc_info.value.errors(include_url=False) == [
        {
            "input": {},
            "loc": ("my_int",),
            "msg": "Field required",
            "type": "missing",
        },
        {
            "input": {},
            "loc": ("my_string",),
            "msg": "Field required",
            "type": "missing",
        },
    ]


def test_set_partial_with_kwargs() -> None:
    settings = PartialSettings(my_int=44, my_string="string with spaces")
    assert settings.my_bool is False
    assert settings.my_int == 44
    assert settings.my_string == "string with spaces"


def test_set_partial_with_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("foobar_my_int", "99")
    monkeypatch.setenv("foobar_my_string", "string with spaces")
    settings = PartialSettings()
    assert settings.my_bool is False
    assert settings.my_int == 99
    assert settings.my_string == "string with spaces"


def test_set_nested_with_kwargs() -> None:
    settings = NestedSettings(
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
    monkeypatch: MonkeyPatch,
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
    settings = NestedSettings()
    assert settings.cake.layers == [
        Layer(name="ice cream", thick=True),
        Layer(name="meringue", thick=False),
    ]
    assert settings.cake.num_candles == 9
