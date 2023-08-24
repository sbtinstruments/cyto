from pydantic import BaseModel


class CliExtras(BaseModel):
    """CLI-specific model settings."""

    # Exclude this setting from the CLI.
    # Use this for settings that are difficult/impossible to parse in via the
    # CLI. E.g., functions or classes.
    exclude: bool = False
    # Force click to not parse the corresponding option
    force_unprocessed: bool = False
    # Force click to parse the corresponding option as JSON
    force_json: bool = False
    # Use a custom "disable" flag. Only valid for boolean fields.
    # Defaults to the "enable" name prefixed with "no-". E.g.: "debug" becomes
    # "no-debug".
    # Don't prefix the disable flag with "--".
    disable_flag: str | None = None
