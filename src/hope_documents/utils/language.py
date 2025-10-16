from typing import Any


def fqn(obj: Any) -> str:
    """Return the fully qualified name of the object."""
    return f"{obj.__module__}.{obj.__qualname__}"


def parse_bool(v: Any) -> bool:
    return v in ["True", "true", "1", True, "y", "Y", "yes", "Yes"]
