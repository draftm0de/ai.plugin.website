"""Validator for the JSON Schema subset used by website.schema.json.

Supported keywords: type, const, enum, pattern, minLength, minimum, maximum,
uniqueItems, required, properties, additionalProperties (false), items, $ref (#/$defs/...).
An unknown keyword in the schema is an error, so the schema cannot silently stop being checked.
"""
import re

KNOWN = {"$schema", "$defs", "$ref", "title", "type", "const", "enum", "pattern", "minLength", "minimum",
         "maximum", "uniqueItems", "required", "properties", "additionalProperties", "items"}


def _type_ok(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    raise ValueError(f"unsupported type '{name}' in schema")


def validate(instance, schema, root=None, path="$") -> list:
    root = root or schema
    unknown = set(schema) - KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node[part]
        return validate(instance, node, root, path)
    errors = []
    if "type" in schema and not _type_ok(instance, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: '{instance}' does not match {schema['pattern']}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: must not be empty")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} is below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} is above {schema['maximum']}")
    if isinstance(instance, list):
        if schema.get("uniqueItems") and len({repr(i) for i in instance}) != len(instance):
            errors.append(f"{path}: items must be unique")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors += validate(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing '{key}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}: unknown property '{key}'")
        for key, sub in props.items():
            if key in instance:
                errors += validate(instance[key], sub, root, f"{path}.{key}")
    return errors
