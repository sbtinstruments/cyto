from typing import Dict, List, Tuple, Type

import pytest
from pydantic import BaseModel, BaseSettings

from cyto.settings import autofill


class Track(BaseModel):
    title: str
    is_remix: bool = False

    class Config:
        extra = "forbid"


class Album(BaseModel):
    author: str
    title: str = "No title"
    tracks: List[Track] = []


class Selection(BaseModel):
    name: str
    tracks: List[Track] = []
    albums: List[Album] = []
    metadata: Dict[str, str] = {}


class MyTunesSettings(BaseSettings):
    theme: str
    volume: int = 80
    shuffle: bool = True
    translations: Dict[str, str] = {
        "repeat": "repetir",
        "shuffle": "barajar",
    }


@pytest.fixture
def mytunes_settings() -> Type[MyTunesSettings]:
    return autofill(name="mytunes")(MyTunesSettings)


class WinLampSettings(BaseSettings):
    favourite_genres: List[str] = ["Classical", "Electronic"]
    version_info: Tuple[str, int, int, int] = ("1.2.0", 1, 2, 0)


@pytest.fixture
def winlamp_settings() -> Type[WinLampSettings]:
    return autofill(name="winlamp")(WinLampSettings)


class DotifySettings(BaseSettings):
    featured_album: Album


@pytest.fixture
def dotify_settings() -> Type[DotifySettings]:
    return autofill(name="dotify")(DotifySettings)


class Zoobar2000Settings(BaseSettings):
    playlist: List[Track] = [
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
def zoobar2000_settings() -> Type[Zoobar2000Settings]:
    return autofill(name="zoobar2000")(Zoobar2000Settings)


class NoDefaultSettings(BaseSettings):
    flag: bool
    numbers: List[int]
    strings: Dict[str, str]


@pytest.fixture
def nodefault_settings() -> Type[NoDefaultSettings]:
    return autofill(name="nodefault")(NoDefaultSettings)
