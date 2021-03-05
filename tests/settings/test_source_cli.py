# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere precense. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# pylint: disable=too-few-public-methods
# This warning doesn't make sense for the `Config` class on a `BaseModel`.

# type: ignore[no-untyped-def]
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
from typing import Dict, List, Tuple, Type

import click
import pytest
from pydantic import BaseModel, BaseSettings, Field, ValidationError

from cyto.settings import autofill
from cyto.settings.sources.cli import CliExtras

from ..conftest import Argv


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
    large_text: bool = Field(default=True, cli=CliExtras(disable_flag="small_text"))
    translations: Dict[str, str] = {
        "repeat": "repetir",
        "shuffle": "barajar",
    }


class WinLampSettings(BaseSettings):
    favourite_genres: List[str] = ["Classical", "Electronic"]
    version_info: Tuple[str, int, int, int] = ("1.2.0", 1, 2, 0)


class DotifySettings(BaseSettings):
    featured_album: Album


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


class CustomCliSettings(BaseSettings):
    numbers: List[int] = Field([1, 2, 3], cli=CliExtras(force_json=True))

    class Config:
        extra = "forbid"


class NoDefaultSettings(BaseSettings):
    flag: bool
    numbers: List[int]
    strings: Dict[str, str]


class Bobby(BaseModel):
    tables: int = 2


class HackerSettings(BaseSettings):
    bobby__tables: int = 1
    bobby: Bobby = Bobby()


@pytest.fixture
def mytunes_settings() -> Type[MyTunesSettings]:
    return autofill(name="mytunes")(MyTunesSettings)


@pytest.fixture
def winlamp_settings() -> Type[WinLampSettings]:
    return autofill(name="winlamp")(WinLampSettings)


@pytest.fixture
def dotify_settings() -> Type[DotifySettings]:
    return autofill(name="dotify")(DotifySettings)


@pytest.fixture
def zoobar2000_settings() -> Type[Zoobar2000Settings]:
    return autofill(name="zoobar2000")(Zoobar2000Settings)


@pytest.fixture
def customcli_settings() -> Type[CustomCliSettings]:
    return autofill(name="customcli")(CustomCliSettings)


@pytest.fixture
def nodefault_settings() -> Type[NoDefaultSettings]:
    return autofill(name="nodefault")(NoDefaultSettings)


@pytest.fixture
def hacker_settings() -> Type[HackerSettings]:
    return autofill(name="hacker")(HackerSettings)


def test_basic_field(
    mytunes_settings: Type[MyTunesSettings],
    argv: Argv,
) -> None:
    # It raises an exception when you forget a required field
    with pytest.raises(ValidationError) as exc_info:
        mytunes_settings()
    assert exc_info.value.errors() == [
        {
            "loc": ("theme",),
            "msg": "field required",
            "type": "value_error.missing",
        },
    ]
    # Set the required field
    argv.append("--theme", "dark")
    settings = mytunes_settings()
    assert settings.theme == "dark"
    # Non-required fields get their default value
    assert settings.volume == 80
    assert settings.shuffle is True
    assert settings.translations == {
        "repeat": "repetir",
        "shuffle": "barajar",
    }
    # You can override the defaults
    argv.append("--volume", 100)
    # Note the "no-" prefix to disable a boolean
    argv.append("--no-shuffle")
    # We use the dedicated "disable flag" to switch of `large_text`
    argv.append("--small-text")
    # English to Danish
    argv.append(
        "--translations",
        """{
            "play": "spil",
            "back": "tilbage",
            "forward": "frem"
        }""",
    )
    settings = mytunes_settings()
    assert settings.volume == 100
    assert settings.shuffle is False
    assert settings.large_text is False
    assert settings.translations == {
        "play": "spil",
        "back": "tilbage",
        "forward": "frem",
    }
    # If you set a non-existing field, it raises an exception
    argv.append("--this-does-not-exist", 42)
    with pytest.raises(click.NoSuchOption):
        mytunes_settings()
    # We can't control if you accidentally passed in, e.g., a real
    # number instead of a string. This is because strings can take
    # on arbitrary values.
    argv.assign("--theme", 3.14)
    settings = mytunes_settings()
    assert settings.theme == "3.14"
    # We can, however, ensure that, e.g., integers are valid
    argv.append("--volume", "loudest")
    with pytest.raises(click.BadParameter):
        mytunes_settings()


def test_model_field(
    dotify_settings: Type[dotify_settings],
    argv: Argv,
) -> None:
    # The `featured_album` field exists but it's a model. You can't
    # set the model with JSON.
    argv.assign("--featured-album", '{"author": "Beethoven"}')
    with pytest.raises(click.NoSuchOption):
        dotify_settings()
    # Instead, you must set the individual fields.
    argv.assign("--featured-album.author", "Beethoven")
    settings = dotify_settings()
    assert settings.featured_album.author == "Beethoven"
    # The other fields have default values
    assert settings.featured_album.title == "No title"
    assert settings.featured_album.tracks == []
    # You can override the defaults
    argv.append("--featured-album.title", "The Complete Symphonies")
    settings = dotify_settings()
    assert settings.featured_album.title == "The Complete Symphonies"


def test_list_field(
    winlamp_settings: Type[WinLampSettings],
    argv: Argv,
) -> None:
    # Let's see if the default settings are there
    settings = winlamp_settings()
    assert settings.favourite_genres == ["Classical", "Electronic"]
    # Now we override the defaults
    argv.append("--favourite-genres", "Pop")
    settings = winlamp_settings()
    assert settings.favourite_genres == ["Pop"]
    # You can specify additional elements as well
    argv.append("--favourite-genres", "Rock")
    argv.append("--favourite-genres", "Reggae")
    settings = winlamp_settings()
    assert settings.favourite_genres == ["Pop", "Rock", "Reggae"]
    # You can't give multiple values at once
    argv.append("--favourite-genres", "Jazz", "Funk")
    with pytest.raises(click.UsageError):
        settings = winlamp_settings()
    # You can't use JSON array notation. It will simply
    # parse as a string, which is probably not what you want.
    argv.assign("--favourite-genres", '["Soul", "Techno"]')
    settings = winlamp_settings()
    assert settings.favourite_genres[0] == '["Soul", "Techno"]'


def test_tuple_field(
    winlamp_settings: Type[WinLampSettings],
    argv: Argv,
) -> None:
    # Let's check the defaults
    settings = winlamp_settings()
    assert settings.version_info == ("1.2.0", 1, 2, 0)
    # Override the defaults
    argv.append("--version-info", "3.0.9", 3, 0, 9)
    settings = winlamp_settings()
    assert settings.version_info == ("3.0.9", 3, 0, 9)
    # It's an error to only provide some of the arguments
    argv.assign("--version-info", "5.0.0", 5)
    with pytest.raises(click.BadOptionUsage):
        settings = winlamp_settings()


def test_list_of_models(
    zoobar2000_settings: Type[Zoobar2000Settings],
    argv: Argv,
) -> None:
    # Let's check (some of) the defaults
    settings = zoobar2000_settings()
    assert settings.playlist[1].title == "Für Elise"
    assert settings.playlist[1].is_remix is False
    # Now we override the defaults. Note the JSON notation.
    argv.append("--playlist", '{"title": "Stairway to Heaven"}')
    settings = zoobar2000_settings()
    assert settings.playlist == [Track(title="Stairway to Heaven")]
    # We can add additional items
    argv.append("--playlist", '{"title": "Like a Rolling Stone"}')
    argv.append(
        "--playlist", '{"title": "Electric Feel (Justice Remix)", "is_remix": true}'
    )
    settings = zoobar2000_settings()
    assert settings.playlist == [
        Track(title="Stairway to Heaven"),
        Track(title="Like a Rolling Stone"),
        Track(title="Electric Feel (Justice Remix)", is_remix=True),
    ]
    # It raises an exception if we specify invalid fields
    argv.append(
        "--playlist",
        """{
            "song": "In for the Kill (Skream Remix)",
            "is_remix": true
        }""",
    )
    with pytest.raises(ValidationError):
        settings = zoobar2000_settings()
    # Note that `Track` explicitly forbids extra fields. Therefore,
    # it raises an exception if we include extra fields in the JSON.
    argv.assign(
        "--playlist",
        """{
            "title": "In for the Kill (Skream Remix)",
            "is_remix": true,
            "rating": 9
        }""",
    )
    with pytest.raises(ValidationError) as exc_info:
        settings = zoobar2000_settings()
    assert exc_info.value.errors() == [
        {
            "loc": ("playlist", 0, "rating"),
            "msg": "extra fields not permitted",
            "type": "value_error.extra",
        },
    ]
    # Invalid JSON is an error as well
    argv.assign(
        "--playlist",
        """{
            'title': "In for the Kill (Skream Remix)",
            "is_remix": true
        }""",
    )
    with pytest.raises(click.BadParameter):
        settings = zoobar2000_settings()


def test_complex_hierarchy(
    zoobar2000_settings: Type[Zoobar2000Settings],
    argv: Argv,
) -> None:
    # Let's try to change the defaults of a deep hierarchy of
    # lists and models.
    argv.append("--user-favourites.name", "My top selection")
    argv.append(
        "--user-favourites.albums",
        """{
            "author": "Guns N' Roses",
            "title": "Appetite For Destruction",
            "tracks": [
                { "title": "Welcome To The Jungle" },
                { "title": "It's So Easy" },
                { "title": "Nightrain" }
            ]
        }""",
    )
    argv.append(
        "--user-favourites.albums",
        """{
            "author": "Caribou",
            "title": "Swim",
            "tracks": [
                { "title": "Odessa" },
                { "title": "Sun" },
                { "title": "Kaili" }
            ]
        }""",
    )
    argv.append(
        "--user-favourites.metadata",
        """{
            "created_on": "2019-09-09",
            "last_updated": "2020-01-24"
        }""",
    )
    settings = zoobar2000_settings()
    assert settings.user_favourites.name == "My top selection"
    assert settings.user_favourites.albums == [
        Album(
            author="Guns N' Roses",
            title="Appetite For Destruction",
            tracks=[
                Track(title="Welcome To The Jungle"),
                Track(title="It's So Easy"),
                Track(title="Nightrain"),
            ],
        ),
        Album(
            author="Caribou",
            title="Swim",
            tracks=[
                Track(title="Odessa"),
                Track(title="Sun"),
                Track(title="Kaili"),
            ],
        ),
    ]
    assert settings.user_favourites.metadata == {
        "created_on": "2019-09-09",
        "last_updated": "2020-01-24",
    }
    # The settings that we didn't change are still at their defaults
    assert settings.user_favourites.tracks == []


def test_force_json(customcli_settings: CustomCliSettings, argv: Argv) -> None:

    # Test that the default still works
    settings = customcli_settings()
    assert settings.numbers == [1, 2, 3]
    # Let's try to override the default with some JSON
    argv.append("--numbers", "[9, 8, 7]")
    settings = customcli_settings()
    assert settings.numbers == [9, 8, 7]
    # Since we use JSON, we if we specify the option again, it will simply override
    # the previous setting,
    argv.append("--numbers", "[6, 5, 4]")
    settings = customcli_settings()
    assert settings.numbers == [6, 5, 4]
    # Of course, the JSON must adhere to the type constraints
    argv.append("--numbers", '["a", "b", "c"]')
    with pytest.raises(ValidationError):
        settings = customcli_settings()
    # Let's try to cheat it with an empty object
    argv.append("--numbers", "{}")
    with pytest.raises(ValidationError):
        settings = customcli_settings()


def test_no_defaults(nodefault_settings: NoDefaultSettings, argv: Argv) -> None:
    # Raises if we don't fill out the defaults
    with pytest.raises(ValidationError):
        nodefault_settings()
    # Let's try to fill them out
    argv.append("--flag")
    argv.append("--numbers", 2, "--numbers", 3)
    argv.append("--strings", '{"key": "value"}')
    nodefault_settings()


def test_precedence(
    monkeypatch,
    mytunes_settings: Type[MyTunesSettings],
    argv: Argv,
) -> None:
    # We set a setting via an environment variable
    monkeypatch.setenv("mytunes_theme", "abyss")
    settings = mytunes_settings()
    assert settings.theme == "abyss"
    # We also set it via CLI
    argv.append("--theme", "solaris")
    settings = mytunes_settings()
    assert settings.theme == "solaris"
    # Let's try with a keyword argument in the mix as well
    settings = mytunes_settings(theme="monokai")
    assert settings.theme == "monokai"


def test_edge_cases(argv: Argv, hacker_settings: HackerSettings) -> None:
    # Fields such as `bobby__tables` conflict with the default
    # internal delimiter "__".
    with pytest.raises(ValueError):
        hacker_settings()

    # The internal delimiter must be a python identifier
    zoobar2000_settings = autofill(
        "zoobar2000",
        cli_settings={"internal_delimiter": "."},
    )(Zoobar2000Settings)
    with pytest.raises(ValueError):
        zoobar2000_settings()

    # Fields such as `large_text` conflict with the delimiter "_"
    zoobar2000_settings = autofill(
        "zoobar2000",
        cli_settings={"delimiter": "_"},
    )(Zoobar2000Settings)
    with pytest.raises(ValueError):
        zoobar2000_settings()

    # Likewise, when we convert the `large_text` field into the `large-text`
    # option, the latter conflicts with the delimiter "-".
    zoobar2000_settings = autofill(
        "zoobar2000",
        cli_settings={"delimiter": "-"},
    )(Zoobar2000Settings)
    with pytest.raises(ValueError):
        zoobar2000_settings()

    # The (external) delimiter can be the same as the internal delimiter
    zoobar2000_settings = autofill(
        "zoobar2000",
        cli_settings={"delimiter": "__", "internal_delimiter": "__"},
    )(Zoobar2000Settings)
    zoobar2000_settings()


def test_help(
    zoobar2000_settings: Type[Zoobar2000Settings],
    argv: Argv,
) -> None:
    argv.append("--help")
    with pytest.raises(SystemExit):
        zoobar2000_settings()
