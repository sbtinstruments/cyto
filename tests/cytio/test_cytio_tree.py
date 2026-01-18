#
# We want to keep the tests very explicit and separate the context managers into
# their own `with` statements. Therefore, we disable:
#
#     SIM117 [*] Use a single `with` statement with multiple contexts instead of
#     nested `with` statements
#
# ruff: noqa: SIM117
from datetime import datetime

import pytest

from cyto.cytio.tree import fetch, patch
from cyto.cytio.tree.current_tree import plant_tree
from cyto.factory import FACTORY
from cyto.model import FrozenModel

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class UnitValue(FrozenModel):
    unit: str
    value: float


class ScrollWheel(FrozenModel):
    mileage: UnitValue = UnitValue(unit="km", value=0)


class Mouse(FrozenModel):
    clicks: int = 0
    wheel: ScrollWheel = ScrollWheel()


FACTORY.register_product(source="default", factory=lambda _: Mouse())


async def test_fetch_without_tree() -> None:
    with pytest.raises(
        RuntimeError, match=r"There isn't a path from the current task to a root node"
    ):
        fetch(Mouse)


async def test_fetch_produce_from_factory() -> None:
    with plant_tree():
        # First fetch automatically produces a value through `FACTORY`
        mouse1 = fetch(Mouse)
        isinstance(mouse1, Mouse)
        assert mouse1.clicks == 0
        assert mouse1.wheel.mileage.value == 0
        assert mouse1.wheel.mileage.unit == "km"

        # Subsequent fetch gets the stored value
        mouse2 = fetch(Mouse)
        assert mouse1 is mouse2


async def test_fetch_produce_without_store() -> None:
    with plant_tree():
        # First fetch automatically produces a value through `FACTORY`
        mouse1 = fetch(Mouse, store_produced_instance=False)
        # Subsequent fetch creates a new value (and stores it!)
        mouse2 = fetch(Mouse, store_produced_instance=True)
        assert mouse1 is not mouse2
        assert mouse1 == mouse2
        # If we fetch again, we get the latest stored value
        mouse3 = fetch(Mouse)
        assert mouse2 is mouse3


async def test_noop_patch() -> None:
    with plant_tree():
        # With the empty dict, patch acts like a regular `fetch`
        with patch(Mouse, {}) as mouse1:
            isinstance(mouse1, Mouse)
            assert mouse1.clicks == 0
            # Note that we get the very same instance back on a subsequent `fetch`
            # because `store_produced_instance=True` for all `patch` calls.
            mouse2 = fetch(Mouse)
            assert mouse1 == mouse2


async def test_simple_patch() -> None:
    with plant_tree():
        mouse1 = fetch(Mouse)
        assert mouse1.clicks == 0
        with patch(Mouse, {"clicks": 42}) as mouse2:
            assert mouse2.clicks == 42
            mouse3 = fetch(Mouse)
            assert mouse3.clicks == 42
        mouse4 = fetch(Mouse)
        assert mouse4.clicks == 0


async def test_nested_patch_of_leaf_field() -> None:
    with plant_tree():
        mouse1 = fetch(Mouse)
        assert mouse1.wheel.mileage.value == 0
        # Nested patch that goes all the way to a "leaf" field
        with patch(Mouse, {"wheel.mileage.value": 133.7}) as mouse2:
            assert mouse2.wheel.mileage.value == 133.7
            mouse3 = fetch(Mouse)
            assert mouse3.wheel.mileage.value == 133.7
        mouse4 = fetch(Mouse)
        assert mouse4.wheel.mileage.value == 0


async def test_nested_patch_of_submodel() -> None:
    with plant_tree():
        mouse1 = fetch(Mouse)
        assert mouse1.wheel.mileage.unit == "km"
        assert mouse1.wheel.mileage.value == 0
        with patch(
            Mouse, {"wheel.mileage": UnitValue(unit="cm", value=73.0)}
        ) as mouse2:
            assert mouse2.wheel.mileage.unit == "cm"
            assert mouse2.wheel.mileage.value == 73.0
            mouse3 = fetch(Mouse)
            assert mouse3.wheel.mileage.unit == "cm"
            assert mouse3.wheel.mileage.value == 73.0
        mouse4 = fetch(Mouse)
        assert mouse4.wheel.mileage.unit == "km"
        assert mouse4.wheel.mileage.value == 0


async def test_erroneous_patch() -> None:
    with plant_tree():
        with pytest.raises(
            ValueError,
            match=(
                r"1 validation error for Mouse\nclicks\n  Input should be a valid "
                r"integer,.*"
            ),
        ):
            with patch(Mouse, {"clicks": "sure, why not"}):
                pass

        with pytest.raises(ValueError, match=r"Input should be a valid dictionary"):
            with patch(Mouse, {"wheel.mileage": 73.1}):
                pass

        with pytest.raises(
            ValueError,
            match=(
                r"1 validation error for Mouse\nwheel\.mileage\.unit\n  "
                r"Input should be a valid string"
            ),
        ):
            with patch(Mouse, {"wheel.mileage.unit": datetime}):
                pass
