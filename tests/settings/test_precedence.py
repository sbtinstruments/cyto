# pylint: disable=missing-function-docstring,missing-class-docstring

# pytest fixtures may have effects just by their mere presence. E.g., the
# `Argv` fixture that clears all arguments per default. Since this is the case,
# the "unused argument" warning is moot.
# pylint: disable=unused-argument

# pylint: disable=redefined-outer-name
# Unfortunately, pylint matches fixtures based on argument names.
# Therefore, redefinitions can't be avoided.

# mypy: disable-error-code=no-untyped-def
# Hopefully, pytest changes soon so we don't need to ignore no-untyped-def anymore.
# See https://github.com/pytest-dev/pytest/issues/7469
from ..conftest import Argv
from .conftest import DefaultSettings


def test_etc_precedence(
    fs,
    default_settings: type[DefaultSettings],
    argv: Argv,
) -> None:
    fs.create_file("/etc/foobar/0.json", contents='{ "my_int": 0 }')
    fs.create_file("/etc/foobar/1.json", contents='{ "my_int": 1 }')
    fs.create_file("/etc/foobar/2.json", contents='{ "my_int": 2 }')
    settings = default_settings()
    assert settings.my_int == 2
    # Remove a file to make the other files take precedence
    fs.remove_object("/etc/foobar/2.json")
    settings = default_settings()
    assert settings.my_int == 1
    # Remove all files to go back to the default
    fs.remove_object("/etc/foobar/1.json")
    fs.remove_object("/etc/foobar/0.json")
    settings = default_settings()
    assert settings.my_int == 42


def test_etc_vs_cwd_precedence(
    fs,
    default_settings: type[DefaultSettings],
    argv: Argv,
) -> None:
    fs.create_file("/etc/foobar/a.json", contents='{ "my_int": 1 }')
    fs.create_file("./a.foobar.json", contents='{ "my_int": 2 }')
    settings = default_settings()
    assert settings.my_int == 2


def test_cwd_vs_env_precedence(
    fs,
    monkeypatch,
    default_settings: type[DefaultSettings],
    argv: Argv,
) -> None:
    fs.create_file("./a.foobar.json", contents='{ "my_int": 2 }')
    monkeypatch.setenv("foobar_my_int", "3")
    settings = default_settings()
    assert settings.my_int == 3


def test_env_vs_kwarg_precedence(
    monkeypatch,
    default_settings: type[DefaultSettings],
    argv: Argv,
) -> None:
    monkeypatch.setenv("foobar_my_int", "3")
    settings = default_settings(my_int=4)
    assert settings.my_int == 4
