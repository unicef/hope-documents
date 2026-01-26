from django.apps import AppConfig


class Config(AppConfig):
    name = "hope_documents"

    def ready(self) -> None:
        from . import checks  # noqa
        from . import handlers  # noqa
