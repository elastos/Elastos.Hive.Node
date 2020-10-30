from flask import Flask, request

from hive import main
from hive.util.constants import HIVE_MODE_PROD, HIVE_MODE_DEV, HIVE_MODE_TEST

DEFAULT_APP_NAME = 'Hive Node'

app = Flask(DEFAULT_APP_NAME)


def create_app(mode=HIVE_MODE_DEV):
    global app
    main.init_app(app, mode)
    return app


@app.before_request
def handle_chunking():
    """
    Sets the "wsgi.input_terminated" environment flag, thus enabling
    Werkzeug to pass chunked requests as streams; this makes the API
    compliant with the HTTP/1.1 standard.  The gunicorn server should set
    the flag, but this feature has not been implemented.
    """
    transfer_encoding = request.headers.get("Transfer-Encoding", None)
    if transfer_encoding == "chunked":
        request.environ["wsgi.input_terminated"] = True
