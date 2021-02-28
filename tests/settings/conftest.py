from typing import List, Type

import pytest
from pydantic import BaseModel, BaseSettings

from cyto.settings import autofill


class Layer(BaseModel):
    name: str
    thick: bool = False


class Cake(BaseModel):
    layers: List[Layer]
    num_candles: int = 9
    price: int


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
        ],
        price=23,
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
