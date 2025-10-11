from django.apps import AppConfig
from django.db.models.signals import post_migrate

from demo.utils import generate_sample_data


class Config(AppConfig):
    name = "demo"
    verbose_name = "Demo"

    def ready(self):
        pass


post_migrate.connect(generate_sample_data)
