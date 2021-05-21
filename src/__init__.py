# -*- coding: utf-8 -*-
import logging.config
import yaml
from flask_cors import CORS
from flask import Flask, request
from werkzeug.routing import BaseConverter

from hive import main
from hive.settings import hive_setting
from hive.util.constants import HIVE_MODE_PROD, HIVE_MODE_DEV
from hive.util.did.did_init import init_did_backend
from src import view
from src.utils.http_response import UnauthorizedException


class RegexConverter(BaseConverter):
    """ Support regex on url match """
    def __init__(self, url_map, *items):
        super().__init__(url_map)
        self.regex = items[0]


app = Flask('Hive Node V2')
app.url_map.converters['regex'] = RegexConverter


@app.before_request
def before_request():
    """
    Sets the "wsgi.input_terminated" environment flag, thus enabling
    Werkzeug to pass chunked requests as streams; this makes the API
    compliant with the HTTP/1.1 standard.  The gunicorn server should set
    the flag, but this feature has not been implemented.
    """
    transfer_encoding = request.headers.get("Transfer-Encoding", None)
    if transfer_encoding == "chunked":
        request.environ["wsgi.input_terminated"] = True


def _init_log():
    print("init log")
    with open('logging.conf') as f:
        logging.config.dictConfig(yaml.load(f, Loader=yaml.FullLoader))
    logfile = logging.getLogger('file')
    log_console = logging.getLogger('console')
    logfile.debug("Debug FILE")
    log_console.debug("Debug CONSOLE")


def create_app(mode=HIVE_MODE_PROD, hive_config='/etc/hive/.env'):
    global app
    hive_setting.init_config(hive_config)
    _init_log()
    init_did_backend()
    main.init_app(app, mode)
    view.init_app(app, mode)
    if mode == HIVE_MODE_DEV:
        CORS(app, supports_credentials=True)
        print("hive node cors supported")
    logging.getLogger("create_app").debug("create_app")
    return app
