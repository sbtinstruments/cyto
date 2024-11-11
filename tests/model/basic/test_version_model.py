# ruff: noqa: PLR2004
from typing import Annotated

import pytest
from pydantic import BaseModel, Field, ValidationError

from cyto.model.basic import Version, VersionField


def test_version_model_validate() -> None:
    with pytest.raises(ValidationError):
        Version.model_validate("0")

    with pytest.raises(ValidationError):
        Version.model_validate("0.")

    ver = Version.model_validate("0.0")
    assert ver == Version(major=0, minor=0, patch=0)

    ver = Version.model_validate("0.0.0")
    assert ver == Version(major=0, minor=0, patch=0)

    with pytest.raises(ValidationError):
        Version.model_validate("1.2.3d")

    ver = Version.model_validate("2024.03f")
    assert ver == Version(major=2024, minor=3, patch=5)

    ver = Version.model_validate("1.0-beta.0-dirty")
    assert ver == Version(major=1, minor=0, patch=0, modifiers=("beta.0", "dirty"))


def test_version_field() -> None:
    class SystemInfo(BaseModel):
        software_ver: Annotated[VersionField, Field(default="2024.03c")]
        hardware_ver: VersionField = "1.0-alpha.3"  # type: ignore[assignment]

    sysinfo = SystemInfo()  # type: ignore[call-arg]
    assert isinstance(sysinfo.software_ver, Version)
    assert sysinfo.software_ver.major == 2024
    assert sysinfo.software_ver.minor == 3
    assert sysinfo.software_ver.patch == 2
    assert not sysinfo.software_ver.modifiers

    assert isinstance(sysinfo.hardware_ver, Version)
    assert sysinfo.hardware_ver.major == 1
    assert sysinfo.hardware_ver.minor == 0
    assert sysinfo.hardware_ver.patch == 0
    assert sysinfo.hardware_ver.modifiers == ("alpha.3",)
