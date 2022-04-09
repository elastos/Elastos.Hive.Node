import logging

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry_hook(sentry_dsn):
    """
    Hook the excepthook to send necessary errors to sentry.
    """
    # INFO: add logging integration to disable.
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=None  # Send errors as events, None to disable
    )
    sentry_sdk.init(dsn=sentry_dsn, 
                    integrations=[FlaskIntegration(), logging_integration],
                    traces_sample_rate=1.0)
