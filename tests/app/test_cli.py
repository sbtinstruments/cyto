from pydantic import BaseModel

from cyto.app import App, AppBaseSettings

from ..conftest import Argv


def test_flat_args(argv: Argv) -> None:
    argv.append(
        "--cream_and_sugar",
        "True",
        "--debug",
        "True",
        "--background",
        "False",
        "--roast_level",
        "42",
    )

    class FooBarSettings(AppBaseSettings):
        cream_and_sugar: bool
        roast_level: int = 3

    async def main(settings: FooBarSettings) -> None:
        assert settings.cream_and_sugar is True
        assert settings.debug is True
        assert settings.background is False
        assert settings.roast_level == 42

    App.launch(main)


def test_nested_args(argv: Argv) -> None:
    argv.append(
        "--duration",
        "42",
        "--roast.heat",
        "12",
    )

    class Roast(BaseModel):
        duration: int = 60
        heat: int = 30

    class CoffeeMateSettings(AppBaseSettings):
        roast: Roast = Roast()
        # Let's try to confuse it with these top-level fields with
        # the exact same names as in `Roast`.
        duration: int = 20
        heat: int = 10

    async def main(settings: CoffeeMateSettings) -> None:
        assert settings.roast.duration == 60
        assert settings.roast.heat == 12
        assert settings.duration == 42
        assert settings.heat == 10

    App.launch(main)
