# pylint: disable=missing-function-docstring,missing-class-docstring

from contextlib import AsyncExitStack

import pytest
from anyio import sleep
from anyio.abc import TaskGroup

from cyto.app import App, Settings


def test_inject_nothing() -> None:
    async def main() -> None:
        pass

    App.launch(main)


def test_injection_settings() -> None:
    async def main(settings: Settings) -> None:
        assert isinstance(settings, Settings)

    App.launch(main)


def test_inject_task_group() -> None:
    async def main(tg: TaskGroup) -> None:
        assert isinstance(tg, TaskGroup)

    App.launch(main)


def test_inject_stack() -> None:
    async def main(stack: AsyncExitStack) -> None:
        assert isinstance(stack, AsyncExitStack)

    App.launch(main)


def test_inject_multiple() -> None:
    # Note that the argument names can be anything. We inject solely based
    # on the type annotation.
    async def main(oh: TaskGroup, hi: AsyncExitStack, there: Settings) -> None:
        assert isinstance(there, Settings)
        assert isinstance(oh, TaskGroup)
        assert isinstance(hi, AsyncExitStack)

    App.launch(main)


def test_inject_missing_anno() -> None:
    # We purposedly omit the annotation, hence the "type: ignore" comment
    # Likewise, we purposedly don't use the argument for anything. We just
    # want to test the inject semantics.
    async def main(stack) -> None:  # type: ignore[no-untyped-def] # pylint: disable=unused-argument
        pass

    with pytest.raises(ValueError):
        App.launch(main)


def test_inject_unknown_anno() -> None:
    # Note that we inject arguments based on the type annotation and not
    # the argument name.
    async def main(stack: int) -> None:  # pylint: disable=unused-argument
        pass

    with pytest.raises(ValueError):
        App.launch(main)


def test_custom_settings() -> None:
    class FooBarSettings(Settings):
        is_meringue_burnt: bool = False

    async def main(settings: FooBarSettings) -> None:
        assert settings.is_meringue_burnt is False

    App.launch(main, FooBarSettings)


def test_returns() -> None:
    async def main() -> int:
        await sleep(0.1)
        return 42

    result = App.launch(main)
    assert result == 42


def test_raises() -> None:
    async def main() -> None:
        await sleep(0.1)
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        App.launch(main)


def test_tasks() -> None:
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


def test_tasks_raises() -> None:
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
