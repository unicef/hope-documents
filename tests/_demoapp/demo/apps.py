from django.apps import AppConfig
from django.db.models.signals import post_migrate


class Config(AppConfig):
    name = "demo"
    verbose_name = "Demo"

    def ready(self):
        from demo.utils import generate_sample_data

        post_migrate.connect(generate_sample_data, sender=self)
