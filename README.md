# Cyto

This is a work-in-progress replacement for `geist`.

## Development


### Python Version

Development requires Python 3.6 or later. Test your python version with:
```shell
python3 --version
```

If you have multiple python installations, you can replace `python3`
with a specific version (e.g., `python3.8`) in the steps below.

### Getting Started

Do the following:

 1. Clone this repository
    ```shell
    git clone git@github.com:sbtinstruments/cyto.git
    ```
 2. Install poetry (for dependency management)
    ```shell
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3
    ```
 3. Optional: Use a local poetry virtual environment
    ```shell
    poetry config --local virtualenvs.in-project true
    ```
    This integrates better with editors such as Visual Studio Code.
 4. Create poetry's virtual environment and get all the dependencies
    ```shell
    poetry install
    ```
 5. Optional: Run the basic QA tools (e.g., isort, black, pylint, mypy) automatically before each commit
    ```shell
    poetry run pre-commit install
    ```

### Quality Assurance (QA) Tools

*All of the tools below automatically run in Jenkins for each
commit pushed to the remote repository. If you installed the
`pre-commit` hooks, all tools (except the tests) automatically
run before each commit too.*

You can always run the QA tools manually. This is useful if you
don't want to install the `pre-commit` hooks.

Run `isort` (for import ordering) manually :

```shell
poetry run isort cyto tests
```

Run `black` (for formatting) manually :

```shell
poetry run black cyto tests
```

Run `pylint` (for linting) manually :

```shell
poetry run pylint cyto tests
```

Run `mypy` (for type checking) manually :

```shell
poetry run mypy cyto tests
```

Run all the above manually (this doesn't require you to install the `pre-commit` hooks):

```shell
poetry run pre-commit run --all-files
```

Run `pytest` manually (for testing):

 1. Install `tox` (for test automation across Python versions)
    ```shell
    python3 -m pip install tox
    ```
 2. Start a tox run:
    ```
    tox
    ```
    From here, `tox` invokes `pytest` in a set of virtual environments.

### Visual Studio Code

We have a default settings file that you can use via the following command:
```shell
cp .vscode/settings.json.default .vscode/settings.json
```
This is optional.