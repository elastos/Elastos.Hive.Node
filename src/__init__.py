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

import os

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CONFIG_FILE = os.path.join(BASE_DIR, 'logging.conf')


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
    with open(CONFIG_FILE) as f:
        logging.config.dictConfig(yaml.load(f, Loader=yaml.FullLoader))
    logfile = logging.getLogger('file')
    log_console = logging.getLogger('console')
    logfile.debug("Debug FILE")
    log_console.debug("Debug CONSOLE")


def create_app(mode=HIVE_MODE_PROD, hive_config='/etc/hive/.env'):
    hive_setting.init_config(hive_config)
    _init_log()
    init_did_backend()
    main.init_app(app, mode)
    view.init_app(app, mode)
    if mode == HIVE_MODE_DEV:
        CORS(app, supports_credentials=True)
        print("hive node cors supported")
    # The logging examples, the output is in CONSOLE and hive.log:
    #   2021-06-15 12:06:08,527 - Initialize - DEBUG - create_app
    #   2021-06-15 12:06:08,527 - root - INFO - [Initialize] create_app is processing now.
    logging.getLogger("Initialize").debug("create_app")
    logging.info('[Initialize] create_app is processing now.')
    return app


def make_port(is_first=False):
    """
    For sphinx documentation tool.
    :return: the app of the flask
    """
    if is_first:
        view.init_app(app, HIVE_MODE_PROD)
    return app
