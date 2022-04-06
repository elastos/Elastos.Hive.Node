import sys

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from src.utils.http_exception import HiveException


def _make_sentry_excepthook(old_excepthook):
    """ Comes from exceptionhook.py of sentry_sdk. """
    # type: (Excepthook) -> Excepthook
    def sentry_sdk_excepthook(type_, value, traceback):
        # type: (Type[BaseException], BaseException, TracebackType) -> None
        if value and isinstance(value, HiveException) or isinstance(value, HiveException):
            # INFO: Skip the exception from normally throwing because of already back to SDK side.
            return

        return old_excepthook(type_, value, traceback)

    return sentry_sdk_excepthook


def init_sentry_hook(sentry_dsn):
    """
    Hook the excepthook to send necessary errors to sentry.
    """
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FlaskIntegration()], traces_sample_rate=1.0)
    sys.excepthook = _make_sentry_excepthook(sys.excepthook)
