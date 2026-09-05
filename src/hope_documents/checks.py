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
_AZURE_NETWORK_ERROR_NAMES = frozenset(
    {
        "ServiceRequestError",
        "ServiceResponseError",
        "ServiceRequestTimeoutError",
        "ServiceResponseTimeoutError",
    }
)


def _is_azure_backend(backend: type[Any]) -> bool:
    return backend.__module__.startswith("storages.backends.azure_storage")


def _is_azure_network_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, OSError)):
        return True
    return type(exc).__name__ in _AZURE_NETWORK_ERROR_NAMES and type(exc).__module__.startswith("azure.")


def _probe_azure_container(storage: Any) -> list[CheckMessage]:
    try:
        # AzureStorage.client is lazy and can raise on invalid config.
        client = getattr(storage, "client", None)
        if client is None or not hasattr(client, "exists"):
            return []
        exists = client.exists()
    except Exception as exc:  # noqa: BLE001
        if _is_azure_network_error(exc):
            return [
                CheckWarning(
                    f"STORAGES['hope'] could not reach Azure: {exc}",
                    hint="A transient network issue should not block deploy; retry if it persists.",
                    id="hope_documents.storages.W002",
                )
            ]
        return [
            Error(
                f"STORAGES['hope'] could not connect to Azure: {exc}",
                hint="Verify FILE_STORAGE_HOPE credentials and container name.",
                id="hope_documents.storages.E003",
            )
        ]

    if not exists:
        return [
            Error(
                "STORAGES['hope'] Azure container does not exist.",
                hint="Create the container or correct FILE_STORAGE_HOPE.",
                id="hope_documents.storages.E003",
            )
        ]
    return []


def _check_hope_backend(backend: type[Any], options: dict[str, Any]) -> list[CheckMessage]:
    is_azure = _is_azure_backend(backend)
    if is_azure and not options:
        return [
            Error(
                "STORAGES['hope'] uses AzureStorage but has empty OPTIONS.",
                hint="Set FILE_STORAGE_HOPE to the same AzureStorage URL as Country Workspace.",
                id="hope_documents.storages.E002",
            )
        ]

    try:
        storage = backend(**options)
    except Exception as exc:  # noqa: BLE001
        return [
            Error(
                f"STORAGES['hope'] could not be constructed: {exc}",
                hint="Verify BACKEND and OPTIONS for STORAGES['hope'].",
                id="hope_documents.storages.E005",
            )
        ]

    if is_azure:
        return _probe_azure_container(storage)

    return [
        CheckWarning(
            "STORAGES['hope'] is not backed by Azure blob storage.",
            hint="Set FILE_STORAGE_HOPE to storages.backends.azure_storage.AzureStorage in deployed environments.",
            id="hope_documents.storages.W001",
        )
    ]


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

    return _check_hope_backend(backend, options)


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
