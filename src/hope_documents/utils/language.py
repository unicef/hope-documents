from typing import Any


def fqn(obj: Any) -> str:
    """Return the fully qualified name of the object."""
    return f"{obj.__module__}.{obj.__qualname__}"
