from typing import Any

from pydantic import BaseModel


# Inspired by: https://github.com/pydantic/pydantic/issues/1270#issuecomment-729555558
def none_as_null(schema: dict[str, Any], model: type[BaseModel]) -> None:
    """Ensure that `Optional` results in a nullable type in the schema.

    Usage example:

        class MyModel(BaseModel):
            my_field: int | None = None

            class Config:
                @staticmethod
                def schema_extra(schema: dict[str, Any], model: type[MyModel]) -> None:
                    none_as_null(schema, model)

    The schema of the above example becomes something like:

        "my_field": {
            "anyOf": [{"type': "int"}, {"type": "null"}],
        }

    """
    for prop, value in schema.get("properties", {}).items():
        assert isinstance(value, dict)
        # retrieve right field from alias or name
        field = [x for x in model.__fields__.values() if x.alias == prop][0]
        if not field.allow_none:
            continue
        # Only one type, e.g., `{'type': 'integer'}``
        if "type" in value:
            any_of = [{"type": value.pop("type")}]
        # Only one $ref, e.g., from other model
        elif "$ref" in value:
            if issubclass(field.type_, BaseModel):
                # add 'title' in schema to have the exact same behaviour as the rest
                value["title"] = field.type_.__config__.title or field.type_.__name__
            any_of = [{"$ref": value.pop("$ref")}]
        # Already an `anyOf`.
        elif "anyOf" in value:
            any_of = value["anyOf"]
        else:
            raise RuntimeError(
                f"Unsupported schema value '{value}' for property '{prop}'"
            )
        any_of.append({"type": "null"})
        value["anyOf"] = any_of
