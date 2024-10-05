# ruff: noqa: PLR2004
import pytest
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsError
from pytest import MonkeyPatch  # noqa: PT013

from cyto.settings import cyto_defaults

from ...conftest import Argv
from ..conftest import (
    Album,
    DotifySettings,
    MyTunesSettings,
    NoDefaultSettings,
    Track,
    WinLampSettings,
    Zoobar2000Settings,
)


@cyto_defaults(name="customcli")
class CustomCliSettings(BaseSettings, extra="forbid"):
    large_text: bool = Field(default=True)
    numbers: list[int] = Field([1, 2, 3])


class Bobby(BaseModel):
    tables: int = 2


@cyto_defaults(name="hacker")
class HackerSettings(BaseSettings):
    bobby__tables: int = 1
    bobby: Bobby = Bobby()


def test_basic_field(argv: Argv) -> None:
    # It raises an exception when you forget a required field
    with pytest.raises(ValidationError) as exc_info:
        MyTunesSettings()
    assert exc_info.value.errors() == [
        {
            "input": {},
            "loc": ("theme",),
            "msg": "Field required",
            "type": "missing",
            "url": "https://errors.pydantic.dev/2.9/v/missing",
        },
    ]
    # Set the required field
    argv.append("--theme", "dark")
    settings = MyTunesSettings()
    assert settings.theme == "dark"
    # Non-required fields get their default value
    assert settings.volume == 80
    assert settings.shuffle is True
    assert settings.translations == {
        "repeat": "repetir",
        "shuffle": "barajar",
    }
    # You can override the defaults
    argv.append("--volume", "100")
    # Note the "no-" prefix to disable a boolean
    argv.append("--shuffle", "false")
    # English to Danish
    argv.append(
        "--translations",
        """{
            "play": "spil",
            "back": "tilbage",
            "forward": "frem"
        }""",
    )
    settings = MyTunesSettings()
    assert settings.volume == 100
    assert settings.shuffle is False
    assert settings.translations == {
        "play": "spil",
        "back": "tilbage",
        "forward": "frem",
    }
    # If you set a non-existing field, it raises an exception
    argv.append("--this-does-not-exist", "42")
    with pytest.raises(SettingsError):
        MyTunesSettings()
    # We can't control if you accidentally passed in, e.g., a real
    # number instead of a string. This is because strings can take
    # on arbitrary values.
    argv.assign("--theme", "3.14")
    settings = MyTunesSettings()
    assert settings.theme == "3.14"
    # We can, however, ensure that, e.g., integers are valid
    argv.append("--volume", "loudest")
    with pytest.raises(ValidationError):
        MyTunesSettings()


def test_model_field(argv: Argv) -> None:
    # The `featured_album` field exists and it's a model. We set the
    # model using JSON.
    argv.assign("--featured_album", '{"author": "Beethoven"}')
    DotifySettings()
    # We can also set the individual fields of the model.
    argv.assign("--featured_album.author", "Beethoven")
    settings = DotifySettings()
    assert settings.featured_album.author == "Beethoven"
    # The other fields have default values
    assert settings.featured_album.title == "No title"
    assert settings.featured_album.tracks == []
    # You can override the defaults
    argv.append("--featured_album.title", "The Complete Symphonies")
    settings = DotifySettings()
    assert settings.featured_album.title == "The Complete Symphonies"


def test_list_field(argv: Argv) -> None:
    # Let's see if the default settings are there
    settings = WinLampSettings()
    assert settings.favourite_genres == ["Classical", "Electronic"]
    # Now we override the defaults
    argv.append("--favourite_genres", "Pop")
    settings = WinLampSettings()
    assert settings.favourite_genres == ["Pop"]
    # You can specify additional elements as well
    argv.append("--favourite_genres", "Rock")
    argv.append("--favourite_genres", "Reggae")
    settings = WinLampSettings()
    assert settings.favourite_genres == ["Pop", "Rock", "Reggae"]
    # You can't give multiple values at once
    argv.append("--favourite_genres", "Jazz", "Funk")
    with pytest.raises(SettingsError):
        settings = WinLampSettings()
    # You can use JSON array notation.
    argv.assign("--favourite_genres", '["Soul", "Techno"]')
    settings = WinLampSettings()
    assert settings.favourite_genres == ["Soul", "Techno"]


def test_tuple_field(argv: Argv) -> None:
    # Let's check the defaults
    settings = WinLampSettings()
    assert settings.version_info == ("1.2.0", 1, 2, 0)
    # Override the defaults using a JSON list
    argv.append("--version_info", '["3.0.9", 3, 0, 9]')
    settings = WinLampSettings()
    assert settings.version_info == ("3.0.9", 3, 0, 9)
    # It's an error to only provide some of the items in the list
    # since we expect a fixed-size tuple
    argv.assign("--version_info", '["5.0.0", 5]')
    with pytest.raises(ValidationError):
        settings = WinLampSettings()


def test_list_of_models(argv: Argv) -> None:
    # Let's check (some of) the defaults
    settings = Zoobar2000Settings()
    assert settings.playlist[1].title == "Für Elise"
    assert settings.playlist[1].is_remix is False
    # Now we override the defaults. Note the JSON notation.
    argv.append("--playlist", '{"title": "Stairway to Heaven"}')
    settings = Zoobar2000Settings()
    assert settings.playlist == [Track(title="Stairway to Heaven")]
    # We can add additional items
    argv.append("--playlist", '{"title": "Like a Rolling Stone"}')
    argv.append(
        "--playlist", '{"title": "Electric Feel (Justice Remix)", "is_remix": true}'
    )
    settings = Zoobar2000Settings()
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
        settings = Zoobar2000Settings()
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
        settings = Zoobar2000Settings()
    assert exc_info.value.errors() == [
        {
            "input": 9,
            "loc": ("playlist", 0, "rating"),
            "msg": "Extra inputs are not permitted",
            "type": "extra_forbidden",
            "url": "https://errors.pydantic.dev/2.9/v/extra_forbidden",
        },
    ]
    # Invalid JSON is an error as well (note the use of the single quote character)
    argv.assign(
        "--playlist",
        """{
            'title': "In for the Kill (Skream Remix)",
            "is_remix": true
        }""",
    )
    with pytest.raises(SettingsError):
        settings = Zoobar2000Settings()


def test_complex_hierarchy(argv: Argv) -> None:
    # Let's try to change the defaults of a deep hierarchy of
    # lists and models.
    argv.append("--user_favourites.name", "My top selection")
    argv.append(
        "--user_favourites.albums",
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
        "--user_favourites.albums",
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
        "--user_favourites.metadata",
        """{
            "created_on": "2019-09-09",
            "last_updated": "2020-01-24"
        }""",
    )
    settings = Zoobar2000Settings()
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


def test_force_json(argv: Argv) -> None:
    # Test that the default still works
    settings = CustomCliSettings()
    assert settings.numbers == [1, 2, 3]
    # Let's try to override the default with some JSON
    argv.append("--numbers", "[9, 8, 7]")
    settings = CustomCliSettings()
    assert settings.numbers == [9, 8, 7]
    # If we specify the option again, it will extend the list with the new values
    argv.append("--numbers", "[6, 5, 4]")
    settings = CustomCliSettings()
    assert settings.numbers == [9, 8, 7, 6, 5, 4]
    # Of course, the JSON must adhere to the type constraints
    argv.append("--numbers", '["a", "b", "c"]')
    with pytest.raises(ValidationError):
        settings = CustomCliSettings()
    # Let's try to cheat it with an empty object
    argv.append("--numbers", "{}")
    with pytest.raises(ValidationError):
        settings = CustomCliSettings()


def test_no_defaults(argv: Argv) -> None:
    # Raises if we don't fill out the defaults
    with pytest.raises(ValidationError):
        NoDefaultSettings()
    # Let's try to fill them out
    argv.append("--flag", "true")
    argv.append("--numbers", "2", "--numbers", "3")
    argv.append("--strings", '{"key": "value"}')
    NoDefaultSettings()


def test_precedence(monkeypatch: MonkeyPatch, argv: Argv) -> None:
    # We set a setting via an environment variable
    monkeypatch.setenv("mytunes_theme", "abyss")
    settings = MyTunesSettings()
    assert settings.theme == "abyss"
    # We also set it via CLI
    argv.append("--theme", "solaris")
    settings = MyTunesSettings()
    assert settings.theme == "solaris"
    # Let's try with a keyword argument in the mix as well
    settings = MyTunesSettings(theme="monokai")
    assert settings.theme == "monokai"


def test_help(argv: Argv) -> None:
    argv.append("--help")
    with pytest.raises(SystemExit):
        Zoobar2000Settings()
