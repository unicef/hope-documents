import logging

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from hope_documents import __version__

from .. import env

SENTRY_DSN = env("SENTRY_DSN")

sentry_logging = LoggingIntegration(
    breadcrumb_level=logging.INFO,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
    level=None,  # Don't capture Sentry logs
)
if SENTRY_DSN:
    # sentry-sdk 3.x replaced send_default_pii with data_collection; its
    # defaults already include user info, headers, cookies and request bodies.
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT"),
        integrations=[
            DjangoIntegration(cache_spans=False),
            sentry_logging,
        ],
        release=__version__,
    )
