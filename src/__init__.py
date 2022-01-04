# -*- coding: utf-8 -*-
import logging.config
import yaml
from flask_cors import CORS
from flask import Flask, request
from werkzeug.routing import BaseConverter
import os

from src.settings import hive_setting
from src.utils_v1.constants import HIVE_MODE_PROD, HIVE_MODE_DEV
from src.utils_v1.did.did_init import init_did_backend
from src import view

from hive import main

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')


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

    # logging the request detail globally.
    def get_user_info():
        from src.utils_v1.auth import did_auth
        user_did, app_did = did_auth()
        return f'{user_did}, {app_did}'

    logging.getLogger('before_request').info(f'enter {request.full_path}, {request.method}, {get_user_info()}')


def init_log():
    print("init log")
    with open(CONFIG_FILE) as f:
        logging.config.dictConfig(yaml.load(f, Loader=yaml.FullLoader))
    logging.getLogger('file').info("Log in file")
    logging.getLogger('console').info("log in console")
    logging.getLogger('src_init').info("log in console and file")
    logging.info("log in console and file with root Logger")


def create_app(mode=HIVE_MODE_PROD, hive_config='/etc/hive/.env'):
    hive_setting.init_config(hive_config)
    init_log()

    logging.getLogger("src_init").info("##############################")
    logging.getLogger("src_init").info("HIVE NODE IS STARTING")
    logging.getLogger("src_init").info("##############################")

    init_did_backend()
    # init v1 APIs
    main.init_app(app, mode)
    view.init_app(app)

    if hive_setting.ENABLE_CORS:
        CORS(app, supports_credentials=True)
    logging.getLogger("src_init").info(f'ENABLE_CORS is {hive_setting.ENABLE_CORS}.')
    logging.getLogger("src_init").info(f'BACKUP_IS_SYNC is {hive_setting.BACKUP_IS_SYNC}.')
    return app


def make_port(is_first=False):
    """
    For sphinx documentation tool.
    :return: the app of the flask
    """
    if is_first:
        view.init_app(app)
    return app
