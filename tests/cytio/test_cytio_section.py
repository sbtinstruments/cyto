# We want to keep the tests very explicit and separate the context managers into
# their own `with` statements. Therefore, we disable:
#
#     SIM117 [*] Use a single `with` statement with multiple contexts instead of
#     nested `with` statements
#
# ruff: noqa: SIM117
from typing import Any

import pytest
from cyto.cytio.tree import fetch
from cyto.cytio.tree.current_tree import plant_tree
from cyto.cytio.tree.section import Section, section

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_section_without_tree() -> None:
    with pytest.raises(
        RuntimeError, match=r"There isn't a path from the current task to a root node"
    ):
        with section("First section"):
            pass


async def test_single_section() -> None:
    with plant_tree():
        with section("First"):
            pass
        task_section = fetch(Section)
        assert task_section.name == "First"
        assert not task_section.children


async def test_two_parallel_root_sections() -> None:
    with plant_tree():
        with section("First"):
            pass
        with pytest.raises(
            RuntimeError,
            match=r"The current task already has a root-level section called 'First'",
        ):
            with section("Second"):
                pass


async def test_two_nested_sections() -> None:
    with plant_tree():
        with section("outer"):
            with section("inner"):
                pass

        task_section = fetch(Section)
        assert _summarize_section(task_section) == {"outer": {"inner": {}}}


async def test_single_task_sections() -> None:
    with plant_tree():
        with section("root"):
            with section("A"):
                with section("A.alpha"):
                    pass
                with section("A.beta"):
                    with section("A.beta.i"):
                        pass
                    with section("A.beta.ii"):
                        pass
                    with section("A.beta.iii"):
                        pass
            with section("B"):
                pass
            with section("C"):
                with section("C.alpha"):
                    with section("C.alpha.i"):
                        pass
                    with section("C.alpha.ii"):
                        pass
                    with section("C.alpha.iii"):
                        pass
                with section("C.beta"):
                    pass

        task_section = fetch(Section)
        assert _summarize_section(task_section) == {
            "root": {
                "A": {
                    "A.alpha": {},
                    "A.beta": {
                        "A.beta.i": {},
                        "A.beta.ii": {},
                        "A.beta.iii": {},
                    },
                },
                "B": {},
                "C": {
                    "C.alpha": {
                        "C.alpha.i": {},
                        "C.alpha.ii": {},
                        "C.alpha.iii": {},
                    },
                    "C.beta": {},
                },
            }
        }


async def test_duplicate_section_names() -> None:
    with plant_tree():
        with section("root"):
            with section("A"):
                pass
            with pytest.raises(ValueError, match=r"Section name already in use"):
                with section("A"):
                    pass


def _summarize_section(section_: Section) -> dict[str, Any]:
    return {
        section_.name: {
            child.name: _summarize_section_inner(child) for child in section_.children
        }
    }


def _summarize_section_inner(section_: Section) -> dict[str, Any]:
    return {child.name: _summarize_section_inner(child) for child in section_.children}
