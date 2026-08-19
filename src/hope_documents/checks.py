import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.checks import CheckMessage, Error, register
from django.core.checks import Warning as CheckWarning
from django.utils.module_loading import import_string

from .config import env

logger = logging.getLogger(__name__)

HOPE_STORAGE_ALIAS = "hope"


def _is_azure_backend(backend: type[Any]) -> bool:
    return backend.__module__.startswith("storages.backends.azure_storage")


def _check_hope_azure_backend(backend: type[Any], options: dict[str, Any]) -> list[CheckMessage]:
    if not options:
        return [
            Error(
                "STORAGES['hope'] uses AzureStorage but has empty OPTIONS.",
                hint="Set FILE_STORAGE_HOPE to the same AzureStorage URL as Country Workspace.",
                id="hope_documents.storages.E002",
            )
        ]

    try:
        storage = backend(**options)
        client = getattr(storage, "client", None)
        if client is not None and hasattr(client, "exists"):
            client.exists()
    except Exception as exc:  # noqa: BLE001
        return [
            Error(
                f"STORAGES['hope'] could not connect to Azure: {exc}",
                hint="Verify FILE_STORAGE_HOPE credentials, container name, and network access.",
                id="hope_documents.storages.E003",
            )
        ]
    return []


@register(deploy=True)
def check_hope_storage(*args: Any, **kwargs: Any) -> list[CheckMessage]:
    """Ensure the shared HOPE blob storage is configured (read-only for OCR)."""
    config = settings.STORAGES.get(HOPE_STORAGE_ALIAS)
    if not config:
        return [
            Error(
                "STORAGES['hope'] is not configured.",
                hint="Set FILE_STORAGE_HOPE.",
                id="hope_documents.storages.E001",
            )
        ]

    backend_path = config.get("BACKEND")
    options = config.get("OPTIONS", {})
    try:
        backend = import_string(backend_path)
    except Exception as exc:  # noqa: BLE001
        return [
            Error(
                f"STORAGES['hope']['BACKEND'] is invalid: {exc}",
                hint="Check the BACKEND path configured for STORAGES['hope'].",
                id="hope_documents.storages.E004",
            )
        ]

    if _is_azure_backend(backend):
        return _check_hope_azure_backend(backend, options)

    try:
        backend(**options)
    except Exception as exc:  # noqa: BLE001
        return [
            Error(
                f"STORAGES['hope'] could not be constructed: {exc}",
                hint="Verify BACKEND and OPTIONS for STORAGES['hope'].",
                id="hope_documents.storages.E005",
            )
        ]

    return [
        CheckWarning(
            "STORAGES['hope'] is not backed by Azure blob storage.",
            hint="Set FILE_STORAGE_HOPE to storages.backends.azure_storage.AzureStorage in deployed environments.",
            id="hope_documents.storages.W001",
        )
    ]


@register(deploy=True)
def check_dirs(*args: Any, **kwargs: Any) -> list[CheckMessage]:
    return [
        Error(
            f"{_dir} '{Path(env(_dir))}' does not exists",
            hint="check your configuration",
            obj=None,
            id="hope_documents.E005",
        )
        for _dir in ("MEDIA_ROOT", "STATIC_ROOT")
        if not Path(env(_dir)).exists()
    ]
