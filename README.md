# Cyto 🦠

## Idiomatic boilerplate and glue code for Python

Cyto is the bridge between an oppinionated selection of Python tech.
Cyto is everything you need to create a modern Python app.
Cyto is the glue and boilerplate code that you no longer have to write yourself.

*Note 2024-08-21*: [pydantic-settings](https://github.com/pydantic/pydantic-settings)
now supports auto-generation of a CLI based on a pydantic model. Therefore, cyto
no longer includes this feature.

## Only pay for what you use

Cyto has *zero* dependencies per default. Opt-in to functionality via *extra*s.

## Installation

Install Cyto along with *all* extras:

```
pip install cyto[all]
```

Or, using uv:

```
uv add cyto[all]
```

### Choose specific extras

If you only want a specific extra, choose that when you install Cyto. E.g.:

```
pip install cyto[settings]  # Automatically pulls in pydantic-settings
```

Similar for uv:

```
uv add cyto[settings]  # Automatically pulls in pydantic-settings
```

## Development

### Python Version

Development requires Python 3.12 or later. Test your python version with:
```shell
python3 --version
```

If you have multiple python installations, you can replace `python3`
with a specific version (e.g., `python3.12`) in the steps below.

### Getting Started

Do the following:

 1. Clone this repository
    ```shell
    git clone git@github.com:sbtinstruments/cyto.git
    ```
 2. Install uv (for dependency management)
    ```shell
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
 3. Create virtual environment and get all dependencies
 and all extra features.
    ```shell
    uv sync --all-extras
    ```

### Quality Assurance (QA) Tools

#### QA Basic Tools

*All QA basic tools automatically run in Jenkins for each commit pushed
to the remote repository.*

The QA basic tools are:

 * `ruff`
 * `mypy`

You can run the QA basic tools manually. This is useful if you
don't want to install the `pre-commit` hooks.

Run the QA basic tools manually with:
```shell
uv run task ruff
uv run task mypy
```

#### QA Test Tools

*All of the tools below automatically run in Jenkins for each
commit pushed to the remote repository.*

The QA test tools are:
 * `pytest` (the test framework itself)
 * `pytest-cov` (for test coverage percentage)

### Visual Studio Code

#### Settings

We have a default settings file that you can use via the following command:
```shell
cp .vscode/settings.json.default .vscode/settings.json
```
This is optional.
