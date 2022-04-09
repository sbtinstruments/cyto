# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere presence. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# type: ignore[no-untyped-def]
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
from typing import Type

from ...conftest import Argv
from ..conftest import Album, MyTunesSettings, Track, Zoobar2000Settings


def test_set_basic_field(
    fs,
    mytunes_settings: Type[MyTunesSettings],
    argv: Argv,
) -> None:
    fs.create_file("/etc/mytunes/first.toml", contents='theme = "dark"')
    fs.create_file("./second.mytunes.toml", contents="volume = 81")
    settings = mytunes_settings()
    assert settings.theme == "dark"
    assert settings.volume == 81
    # Other fields still at their defaults
    assert settings.shuffle is True
    assert settings.translations == {
        "repeat": "repetir",
        "shuffle": "barajar",
    }


def test_complex_hierarchy(
    fs,
    zoobar2000_settings: Type[Zoobar2000Settings],
    argv: Argv,
) -> None:
    contents = """
        [user_favourites]
        name = "My favs"

        [[user_favourites.albums]]
        author = "Guns N' Roses"
        title = "Appetite For Destruction"

        [[user_favourites.albums.tracks]]
        title = "Welcome To The Jungle"

        [[user_favourites.albums.tracks]]
        title = "It's So Easy"

        [[user_favourites.albums.tracks]]
        title = "Nightrain"

        # Partial entry
        [[user_favourites.albums]]
        author = "My own mix"

    """
    fs.create_file("/etc/zoobar2000/a.toml", contents=contents)
    settings = zoobar2000_settings()
    assert settings.user_favourites.name == "My favs"
    assert settings.user_favourites.albums[0] == Album(
        author="Guns N' Roses",
        title="Appetite For Destruction",
        tracks=[
            Track(title="Welcome To The Jungle"),
            Track(title="It's So Easy"),
            Track(title="Nightrain"),
        ],
    )
    assert settings.user_favourites.albums[1] == Album(author="My own mix")


def test_merging(
    fs,
    zoobar2000_settings: Type[Zoobar2000Settings],
    argv: Argv,
) -> None:
    contents = """
        [user_favourites]
        name = "My favs"

        [[user_favourites.albums]]
        author = "Guns N' Roses"
        title = "Appetite For Destruction"

        [[user_favourites.albums]]
        author = "Caribou"
        title = "Swim"
    """
    fs.create_file("/etc/zoobar2000/a.toml", contents=contents)
    settings = zoobar2000_settings()
    assert settings.user_favourites.name == "My favs"
    assert settings.user_favourites.albums == [
        Album(author="Guns N' Roses", title="Appetite For Destruction"),
        Album(author="Caribou", title="Swim"),
    ]
    assert len(settings.user_favourites.albums) == 2

    # As a general rule, entries in files with higher precedence override the
    # entries in other files. So in case of conflict, the high-precedence entry
    # overrides the lower-precedence entry.
    #
    # There is one exception though: When the conflicting entries are objects.
    # In this case, we merge the objects together.

    # `b.toml` assigns a new `Selection` instance to `user_favourites`.
    contents = """
        [user_favourites]
        name = "Top tracks"
    """
    fs.create_file("/etc/zoobar2000/b.toml", contents=contents)
    settings = zoobar2000_settings()
    # As expected, the settings file now reflects the new `Selection` instance
    assert settings.user_favourites.name == "Top tracks"
    # Note that we didn't specify any albums in the new `Selection` instance.
    # The albums from `a.toml` are still there. This is because we merge
    # the `Selection` instances from `a.toml` and `b.toml` under the hood.
    assert settings.user_favourites.albums == [
        Album(author="Guns N' Roses", title="Appetite For Destruction"),
        Album(author="Caribou", title="Swim"),
    ]

    # There is no exception for lists. So, if we specify `albums`, we
    # override any existing entries.
    contents = """
        [user_favourites]

        [[user_favourites.albums]]
        author = "Swae Lee"
    """
    fs.create_file("/etc/zoobar2000/c.toml", contents=contents)
    settings = zoobar2000_settings()
    # We still see the untouched remnants from `b.toml`
    assert settings.user_favourites.name == "Top tracks"
    # The albums themselves, however, are gone. The new list instance from
    # `c.toml` overrides any existing entries.
    assert settings.user_favourites.albums == [Album(author="Swae Lee")]
