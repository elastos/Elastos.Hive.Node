from flask import Flask, request
import logging.config, yaml

from hive import main
from hive.settings import hive_setting
from hive.util.constants import HIVE_MODE_PROD, HIVE_MODE_DEV, HIVE_MODE_TEST

DEFAULT_APP_NAME = 'Hive Node'

app = Flask(DEFAULT_APP_NAME)


def init_log():
    print("init log")
    logging.config.dictConfig(yaml.load(open('logging.conf'), Loader=yaml.FullLoader))
    logfile = logging.getLogger('file')
    log_console = logging.getLogger('console')
    logfile.debug("Debug FILE")
    log_console.debug("Debug CONSOLE")



def create_app(mode=HIVE_MODE_PROD, hive_config='/etc/hive/.env'):
    global app
    init_log()
    main.init_app(app, mode)
    logging.getLogger("create_app").debug("create_app")
    hive_setting.init_config(hive_config)
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
