from .. import env

STREAMING_BROKER_URL = env("STREAMING_BROKER_URL")

if STREAMING_BROKER_URL.startswith("amqp://"):
    STREAMING_BROKER_URL = STREAMING_BROKER_URL.replace("amqp://", "rabbit://", 1)

STREAMING = {
    "BROKER_URL": STREAMING_BROKER_URL,
    "CLIENT_NAME": "hope-documents",
    "MANAGER_CLASS": "streaming.manager.ChangeManager",
    "LISTEN_CALLBACK": "hope_documents.stream.callbacks.handle_event",
    "QUEUES": {
        "ocr_requests": {
            "binding_keys": ["hd.ocr.request"],
        },
    },
}
