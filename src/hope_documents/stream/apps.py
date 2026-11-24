from django.apps import AppConfig


class StreamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hope_documents.stream"
    verbose_name = "Streaming"

    def ready(self) -> None:
        from streaming.manager import initialize_engine  # noqa: PLC0415

        initialize_engine()
