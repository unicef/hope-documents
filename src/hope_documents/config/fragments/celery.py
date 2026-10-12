from .. import env

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_IMPORTS = ["hope_documents.tasks"]
