import os

import celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hope_documents.config.settings")

app = celery.Celery(
    "hope_documents",
    loglevel="error",
    broker=settings.CELERY_BROKER_URL,
)
app.config_from_object("django.conf:settings", namespace="CELERY", force=True)
app.autodiscover_tasks()
