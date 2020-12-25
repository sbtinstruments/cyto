# Cyto 🦠

This is a work-in-progress replacement for `geist`.

## Development

### Python Version

Development requires Python 3.8 or later. Test your python version with:
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
 4. Create poetry's virtual environment and get all dependencies
 and all extra features.
    ```shell
    poetry install --extras all
    ```
 5. Optional: Run the QA basic tools (e.g., isort, black, pylint, mypy) automatically before each commit
    ```shell
    poetry run pre-commit install
    ```

### Quality Assurance (QA) Tools

#### QA Basic Tools

*All QA basic tools automatically run in Jenkins for each commit pushed
to the remote repository. If you installed the `pre-commit` hooks,
all QA basic tools automatically run before each commit too.*

The QA basic tools are:
 * `isort` (for import ordering)
 * `black` (for formatting)
 * `pylint` (for linting)
 * `mypy` (for type checking)

You can run the QA basic tools manually. This is useful if you
don't want to install the `pre-commit` hooks.

Run the QA basic tools manually with:
```shell
poetry run task isort
poetry run task black
poetry run task pylint
poetry run task mypy
```

Run all the basic QA tools manually with a single command:

```shell
poetry run task pre-commit
```

Note that this doesn't require you to install the `pre-commit` hooks.

#### QA Test Tools

*All of the tools below automatically run in Jenkins for each
commit pushed to the remote repository.*

The QA test tools are:
 * `tox` (for automation across Python versions)
 * `pytest` (the test framework itself)
 * `pytest-cov` (for test coverage percentage)

Run the tests manually:

 1. Install `tox`
    ```shell
    python3 -m pip install tox
    ```
 2. Start a tox run:
    ```
    tox
    ```

Note that `tox` invokes `pytest` in a set of virtual environments. Said
virtual environments have nothing to do with poetry's virtual environment. Poetry and tox runs in isolation of each other.

### Visual Studio Code

#### Settings

We have a default settings file that you can use via the following command:
```shell
cp .vscode/settings.json.default .vscode/settings.json
```
This is optional.

#### Python Interpreter

Hopefully, you used the local poetry virtual environment during
installation (the `poetry config --local virtualenvs.in-project true` part). This way, Visual Studio Code automatically finds the
Python interpreter within poetry's virtual environment.

Alternatively, you can point Visual Studio Code to poetry's
global virtual environments folder. Add the following entry
to your `./vscode/settings.json` file:
```json
{ "python.venvPath": "~/.cache/pypoetry/virtualenvs" }
```

Then, you look for the poetry's currently active virtual environment:
```shell
poetry env list
```

Lastly, you use the Visual Studio Code command
`Python: Select Interpreter` and choose the interpreter inside
poetry's currently active virtual environment.