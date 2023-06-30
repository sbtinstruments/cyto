import anyio
import pytest

from cyto.cytio.tree.current_tree import plant_tree
from cyto.cytio.tree.outcome import add_result
from cyto.stout.from_tree import tree_to_outcome
from cyto.stout.keynote import FinalItem, Slide, TentativeItem

pytestmark = pytest.mark.anyio


async def test_gather_outcome() -> None:
    with plant_tree() as tree:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_track_flow)
            tg.start_soon(_measure_bacteria)

    outcome = tree_to_outcome(tree)


async def _track_flow() -> None:
    for i in range(3):
        add_metric(FlowMetric(pump_velocity_target=10 + i, mean_flow_rate=3.0 + i / 2))


async def _measure_bacteria() -> None:
    set_keynote_slide(FinalItem(key="ID", value="A03"))
    set_keynote_slide(TentativeItem(key="intact cells/ml", value=150000))
    set_keynote_slide(TentativeItem(key="intact cells/ml", value=200000))
    set_keynote_slide(TentativeItem(key="intact cells/ml", value=250000))
    set_keynote_slide(FinalItem(key="intact cells/ml", value=250000))


def set_keynote_slide(slide: Slide) -> None:
    keynote = get_result(Keynote)
    matching_slides = [s for s in keynote if s.key == slide.key]
    if len(matching_slides) > 1:
        raise RuntimeError(
            f"Can not set slide since multiple slides matched the '{slide.key}' key"
        )
    if len(matching_slides) == 0:
        keynote += slide
    if len(matching_slides) == 1:
        ...
    set_result(Keynote, keynote)


def add_keynote_slide(slide: Slide) -> None:
    keynote = get_result(Keynote)
    keynote += slide
    set_result(Keynote, keynote)
