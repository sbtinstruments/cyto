# ruff: noqa: PLR2004
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import MonkeyPatch  # noqa: PT013

from .conftest import DefaultSettings


def test_etc_precedence(fs: FakeFilesystem) -> None:
    fs.create_file("/etc/foobar/0.foobar.json", contents='{ "my_int": 0 }')
    fs.create_file("/etc/foobar/1.foobar.json", contents='{ "my_int": 1 }')
    fs.create_file("/etc/foobar/2.foobar.json", contents='{ "my_int": 2 }')
    settings = DefaultSettings()
    assert settings.my_int == 2
    # Remove a file to make the other files take precedence
    fs.remove_object("/etc/foobar/2.foobar.json")
    settings = DefaultSettings()
    assert settings.my_int == 1
    # Remove all files to go back to the default
    fs.remove_object("/etc/foobar/1.foobar.json")
    fs.remove_object("/etc/foobar/0.foobar.json")
    settings = DefaultSettings()
    assert settings.my_int == 42


def test_etc_vs_cwd_precedence(fs: FakeFilesystem) -> None:
    fs.create_file("/etc/foobar/a.foobar.json", contents='{ "my_int": 1 }')
    fs.create_file("./a.foobar.json", contents='{ "my_int": 2 }')
    settings = DefaultSettings()
    assert settings.my_int == 2


def test_cwd_vs_env_precedence(fs: FakeFilesystem, monkeypatch: MonkeyPatch) -> None:
    fs.create_file("./a.foobar.json", contents='{ "my_int": 2 }')
    monkeypatch.setenv("foobar_my_int", "3")
    settings = DefaultSettings()
    assert settings.my_int == 3


def test_env_vs_kwarg_precedence(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("foobar_my_int", "3")
    settings = DefaultSettings(my_int=4)
    assert settings.my_int == 4
