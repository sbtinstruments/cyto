from collections.abc import Callable
from pathlib import Path
from typing import Any


def get_app_name(main_func: Callable[..., Any] | None = None) -> str:
    """Get the name of the running application.

    Optionally, provide the "main" function to help us decide.
    """
    # Use the function name itself if said name is descriptive
    if (
        main_func is not None
        and main_func.__name__ not in ("main",)
        and not main_func.__name__.startswith("_")
    ):
        return main_func.__name__

    # If the function name isn't desciptive, we query the main module
    import __main__ as main  # pylint: disable=import-outside-toplevel

    # Use the module name if the application runs a module
    #
    # `main` looks something like this:
    #
    # >>> main.__name__   : __main__
    # >>> main.__package__: baxter
    # >>> main.__file__   : /media/system/lib/python3.6/site-packages/baxter/__main__.py
    #
    if isinstance(main.__package__, str):
        return main.__package__

    # Use the file name if the application runs directly
    #
    # `main` looks something like this:
    #
    # >>> main.__name__   : __main__
    # >>> main.__package__: None
    # >>> main.__file__   : /media/system/bin/baxter
    #
    # Or, sometimes, like this:
    #
    # >>> main.__file__   : _appster.py
    #
    try:
        main_file = main.__file__
    # Raises `AttributeError` if you, e.g., run python code directly:
    #
    # >>> python -c "import __main__; __main__.__file__"  # Raises AttributeError!
    #
    except AttributeError:
        pass
    else:
        main_file_name = Path(main_file).stem  # Use the stem to avoid file extensions
        # Remove leading and trailing underscores (if any).
        # All in all, a file name like "_appster.py" becomes "appster".
        return main_file_name.strip("_")
    raise RuntimeError("Could not deduce application name")
