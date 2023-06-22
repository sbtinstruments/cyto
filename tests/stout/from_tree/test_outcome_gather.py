import anyio
import pytest

from cyto.cytio.tree.current_tree import plant_tree
from cyto.cytio.tree.outcome import add_result
from cyto.stout.from_tree import tree_to_outcome

pytestmark = pytest.mark.anyio


async def test_gather_outcome() -> None:
    with plant_tree() as tree:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_cook_rice)
            tg.start_soon(_make_stew)

    outcome = tree_to_outcome(tree)
    assert outcome.result == {"ingredients": {"rice", "vegetables"}}


async def _cook_rice() -> None:
    add_result({"ingredients": {"rice"}})


async def _make_stew() -> None:
    await _fry_vegetables()


async def _fry_vegetables() -> None:
    vegetables: set[str] = set()
    with result() as res:
        for veg in ("potato", "tomato", "onion"):
            vegetables.add(veg)
            res.set(
                {
                    "ingredients": vegetables,
                    "salt_amount": 1,
                },
            )
