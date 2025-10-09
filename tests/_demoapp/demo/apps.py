from django.apps import AppConfig


class Config(AppConfig):
    name = "demo"
    verbose_name = "Demo"

    def ready(self):
        from hope_documents.archive.models import Country

        if not Country.objects.exists():
            from demo.utils import generate_sample_data

            generate_sample_data()
