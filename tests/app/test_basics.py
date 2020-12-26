# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere precense. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

from contextlib import AsyncExitStack

import pytest
from anyio import sleep
from anyio.abc import TaskGroup

from cyto.app import App, Settings

from ..conftest import Argv


def test_inject_nothing(argv: Argv) -> None:
    async def main() -> None:
        pass

    App.launch(main)


def test_injection_settings(argv: Argv) -> None:
    async def main(settings: Settings) -> None:
        assert isinstance(settings, Settings)

    App.launch(main)


def test_inject_task_group(argv: Argv) -> None:
    async def main(tg: TaskGroup) -> None:
        assert isinstance(tg, TaskGroup)

    App.launch(main)


def test_inject_stack(argv: Argv) -> None:
    async def main(stack: AsyncExitStack) -> None:
        assert isinstance(stack, AsyncExitStack)

    App.launch(main)


def test_inject_multiple(argv: Argv) -> None:
    # Note that the argument names can be anything. We inject solely based
    # on the type annotation.
    async def main(apple: TaskGroup, banana: AsyncExitStack, grape: Settings) -> None:
        assert isinstance(grape, Settings)
        assert isinstance(apple, TaskGroup)
        assert isinstance(banana, AsyncExitStack)

    App.launch(main)


def test_inject_missing_anno(argv: Argv) -> None:
    # We purposedly omit the annotation, hence the "type: ignore" comment
    # Likewise, we purposedly don't use the argument for anything. We just
    # want to test the inject semantics.
    async def main(stack) -> None:  # type: ignore[no-untyped-def] # pylint: disable=unused-argument
        pass

    with pytest.raises(ValueError):
        App.launch(main)


def test_inject_unknown_anno(argv: Argv) -> None:
    # Note that we inject arguments based on the type annotation and not
    # the argument name.
    async def main(stack: int) -> None:  # pylint: disable=unused-argument
        pass

    with pytest.raises(ValueError):
        App.launch(main)


def test_custom_settings(argv: Argv) -> None:
    class FooBarSettings(Settings):
        is_meringue_burnt: bool = False

    async def main(settings: FooBarSettings) -> None:
        assert settings.is_meringue_burnt is False

    App.launch(main)


def test_returns(argv: Argv) -> None:
    async def main() -> int:
        await sleep(0.1)
        return 42

    result = App.launch(main)
    assert result == 42


def test_raises(argv: Argv) -> None:
    async def main() -> None:
        await sleep(0.1)
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        App.launch(main)


def test_tasks(argv: Argv) -> None:
    result = 0
    num_tasks = 5

    async def _sleep(i: int) -> None:
        await sleep(0.1)
        nonlocal result
        result += i

    async def main(tg: TaskGroup) -> None:
        for i in range(num_tasks):
            await tg.spawn(_sleep, i)

    App.launch(main)
    assert result == sum(range(num_tasks))


def test_tasks_raises(argv: Argv) -> None:
    num_tasks = 5
    failing_task = 3

    async def _sleep(i: int) -> None:
        await sleep(0.1)
        if i == failing_task:
            raise RuntimeError(failing_task)

    async def main(tg: TaskGroup) -> None:
        for i in range(num_tasks):
            await tg.spawn(_sleep, i)

    with pytest.raises(RuntimeError) as excinfo:
        App.launch(main)
    assert str(failing_task) == str(excinfo.value)


def test_custom_app_name(argv: Argv) -> None:
    async def appster(app: App) -> None:
        assert app.name == "appster"

    App.launch(appster)
