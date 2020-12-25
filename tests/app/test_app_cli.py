# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere precense. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

from cyto.app import App, Settings

from ..conftest import Argv


def test_cli(argv: Argv) -> None:
    class FooBarSettings(Settings):
        cream_and_sugar: bool
        roast_level: int = 3

    argv.append(
        "--cream-and-sugar",
        "--debug",
        "--foreground",
        "--roast-level",
        42,
    )

    async def main(settings: FooBarSettings) -> None:
        assert settings.cream_and_sugar is True
        assert settings.debug is True
        assert settings.background is False
        assert settings.roast_level == 42

    App.launch(main)
