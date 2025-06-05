from contextlib import AsyncExitStack

import pytest
from anyio import sleep
from anyio.abc import TaskGroup
from cyto.app import App, AppBaseSettings

pytestmark = pytest.mark.usefixtures("fs")


def test_inject_nothing() -> None:
    async def main() -> None:
        pass

    App.launch(main)


def test_injection_settings() -> None:
    async def main(settings: AppBaseSettings) -> None:
        assert isinstance(settings, AppBaseSettings)

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
    async def main(
        apple: TaskGroup, banana: AsyncExitStack, grape: AppBaseSettings
    ) -> None:
        assert isinstance(grape, AppBaseSettings)
        assert isinstance(apple, TaskGroup)
        assert isinstance(banana, AsyncExitStack)

    App.launch(main)


def test_inject_missing_anno() -> None:
    # We purposely omit the annotation, hence the "type: ignore" comment
    # Likewise, we purposely don't use the argument for anything. We just
    # want to test the inject semantics.
    async def main(stack) -> None:  # type: ignore[no-untyped-def]
        pass

    with pytest.raises(
        ValueError, match='Argument "stack must have a type annotation"'
    ):
        App.launch(main)


def test_inject_unknown_anno() -> None:
    # Note that we inject arguments based on the type annotation and not
    # the argument name.
    async def main(
        stack: int,
    ) -> None:
        pass

    with pytest.raises(
        ValueError,
        match='Argument "stack" has unknown type annotation "<class \'int\'>"',
    ):
        App.launch(main)


def test_custom_settings() -> None:
    class FooBarSettings(AppBaseSettings):
        is_meringue_burnt: bool = False

    async def main(settings: FooBarSettings) -> None:
        assert settings.is_meringue_burnt is False

    App.launch(main)


def test_returns() -> None:
    async def main() -> int:
        await sleep(0.1)
        return 42

    result = App.launch(main)
    assert result == 42


def test_raises() -> None:
    async def main() -> None:
        await sleep(0.1)
        raise RuntimeError

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
            tg.start_soon(_sleep, i)

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
            tg.start_soon(_sleep, i)

    # TODO: Replace with something that targets the `RuntimeError` when
    # pytest gets better ExceptionGroup support.
    #
    # See: https://github.com/pytest-dev/pytest/issues/11538
    with pytest.raises(ExceptionGroup) as _excinfo:
        App.launch(main)


def test_custom_app_name() -> None:
    async def appster(app: App) -> None:
        assert app.name == "appster"

    App.launch(appster)
