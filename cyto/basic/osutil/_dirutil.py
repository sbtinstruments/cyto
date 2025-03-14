import shutil
from pathlib import Path
from typing import Literal

Mode = Literal["children-and-self", "only-children"]


def purge_dir(
    directory: Path,
    *,
    ifnotdir: Literal["return", "raise"] | None = None,
    mode: Mode,
) -> None:
    """Delete every item (directories, folders, links) in the given directory.

    Does so _recursively_.
    """
    if ifnotdir is None:
        ifnotdir = "raise"

    if not directory.is_dir():
        match ifnotdir:
            case "raise":
                raise FileNotFoundError(f"'{directory}' is not a directory")
            case "return":
                return
            case _:
                raise ValueError(f"Unknown value for ifnotdir '{ifnotdir}'")

    match mode:
        case "only-children":
            for child in directory.iterdir():
                if child.is_dir():
                    # Remove directory recursively
                    shutil.rmtree(child)
                else:
                    # Remove file or symbolic link
                    child.unlink()
        case "children-and-self":
            shutil.rmtree(directory)
        case _:
            raise ValueError(f"Unknown mode '{mode}'")
