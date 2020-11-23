# Cyto

This is a work-in-progress replacement for `geist`.

## Development

Development requires Python 3.6 or later. If your `python3` doesn't point to `python3.6` or later, then the following steps won't work.
Test this with:
```shell
> file `which python3`
/usr/bin/python3: symbolic link to python3.6
```

Get the basic tooling:

 1. Clone this repository
    ```
    git clone git@github.com:sbtinstruments/cyto.git
    ```
 2. Install poetry (for dependency management)
    ```shell
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3
    ```
 3. Activate the tooling (e.g., isort, black, pylint, mypy)
    ```shell
    poetry install
    poetry run pre-commit install
    ```

To run the tests:

 1. Install `tox` (for test automation across Python versions)
    ```shell
    python3 -m pip install tox
    ```
 2. Start a tox run:
    ```
    tox
    ```

All of the above also runs in Jenkins for each commit.