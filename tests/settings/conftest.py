from cyto.settings import cyto_defaults
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Track(BaseModel, extra="forbid"):
    title: str
    is_remix: bool = False


class Album(BaseModel):
    author: str
    title: str = "No title"
    tracks: list[Track] = []


class Selection(BaseModel):
    name: str
    tracks: list[Track] = []
    albums: list[Album] = []
    metadata: dict[str, str] = {}


@cyto_defaults(name="mytunes")
class MyTunesSettings(BaseSettings):
    theme: str
    volume: int = 80
    shuffle: bool = True
    translations: dict[str, str] = {
        "repeat": "repetir",
        "shuffle": "barajar",
    }


@cyto_defaults(name="winlamp")
class WinLampSettings(BaseSettings):
    favourite_genres: list[str] = ["Classical", "Electronic"]
    version_info: tuple[str, int, int, int] = ("1.2.0", 1, 2, 0)


@cyto_defaults(name="dotify")
class DotifySettings(BaseSettings):
    featured_album: Album


@cyto_defaults(name="zoobar2000")
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


@cyto_defaults(name="nodefault")
class NoDefaultSettings(BaseSettings):
    flag: bool
    numbers: list[int]
    strings: dict[str, str]


#################################################
# TODO: Replace the classes below with the
# classes above.
#################################################
class Layer(BaseModel):
    name: str
    thick: bool = False


class Cake(BaseModel):
    layers: list[Layer]
    num_candles: int = 9
    price: int


@cyto_defaults(name="foobar")
class DefaultSettings(BaseSettings):
    my_bool: bool = False
    my_int: int = 42
    my_string: str = "Hello test suite"


@cyto_defaults(name="foobar")
class PartialSettings(BaseSettings):
    my_bool: bool = False
    my_int: int
    my_string: str


@cyto_defaults(name="foobar")
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
