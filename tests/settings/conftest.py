import pytest
from pydantic import BaseModel, BaseSettings

from cyto.settings import autofill


class Track(BaseModel):
    title: str
    is_remix: bool = False

    class Config:  # pylint: disable=too-few-public-methods
        extra = "forbid"


class Album(BaseModel):
    author: str
    title: str = "No title"
    tracks: list[Track] = []


class Selection(BaseModel):
    name: str
    tracks: list[Track] = []
    albums: list[Album] = []
    metadata: dict[str, str] = {}


class MyTunesSettings(BaseSettings):
    theme: str
    volume: int = 80
    shuffle: bool = True
    translations: dict[str, str] = {
        "repeat": "repetir",
        "shuffle": "barajar",
    }


@pytest.fixture
def mytunes_settings() -> type[MyTunesSettings]:
    return autofill(name="mytunes")(MyTunesSettings)


class WinLampSettings(BaseSettings):
    favourite_genres: list[str] = ["Classical", "Electronic"]
    version_info: tuple[str, int, int, int] = ("1.2.0", 1, 2, 0)


@pytest.fixture
def winlamp_settings() -> type[WinLampSettings]:
    return autofill(name="winlamp")(WinLampSettings)


class DotifySettings(BaseSettings):
    featured_album: Album


@pytest.fixture
def dotify_settings() -> type[DotifySettings]:
    return autofill(name="dotify")(DotifySettings)


class Zoobar2000Settings(BaseSettings):
    playlist: list[Track] = [
        Track(title="Eine Kleine Nachtmusik"),
        Track(title="Für Elise"),
        Track(title="The Four Seasons"),
    ]
    user_favourites: Selection = Selection(
        name="Your most played albums",
        albums=[
            Album(
                author="Various Artists",
                title="Kompakt: Total 20",
                tracks=[
                    Track(title="Calma Calma"),
                    Track(title="White Becomes Black"),
                    Track(title="Agita"),
                ],
            )
        ],
    )


@pytest.fixture
def zoobar2000_settings() -> type[Zoobar2000Settings]:
    return autofill(name="zoobar2000")(Zoobar2000Settings)


class NoDefaultSettings(BaseSettings):
    flag: bool
    numbers: list[int]
    strings: dict[str, str]


@pytest.fixture
def nodefault_settings() -> type[NoDefaultSettings]:
    return autofill(name="nodefault")(NoDefaultSettings)


#################################################
### TODO: Replace the classes below with the
### classes above.
#################################################
class Layer(BaseModel):
    name: str
    thick: bool = False


class Cake(BaseModel):
    layers: list[Layer]
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
def default_settings() -> type[DefaultSettings]:
    return autofill(name="foobar")(DefaultSettings)


@pytest.fixture
def partial_settings() -> type[PartialSettings]:
    return autofill(name="foobar")(PartialSettings)


@pytest.fixture
def nested_settings() -> type[NestedSettings]:
    return autofill(name="foobar")(NestedSettings)
