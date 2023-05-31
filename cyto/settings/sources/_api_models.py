from pydantic import BaseModel


class CliExtras(BaseModel):
    """CLI-specific model settings."""

    # Force click to parse the corresponding option as JSON
    force_json: bool = False
    # Use a custom "disable" flag. Only valid for boolean fields.
    # Defaults to the "enable" name prefixed with "no-". E.g.: "debug" becomes
    # "no-debug".
    # Don't prefix the disable flag with "--".
    disable_flag: str | None = None
