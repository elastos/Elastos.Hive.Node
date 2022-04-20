# -*- coding: utf-8 -*-
import logging.config
import traceback

import yaml
from flask_cors import CORS
from flask import Flask, request, g
import os

from sentry_sdk import capture_exception

from src.settings import hive_setting
from src.utils.http_exception import HiveException, InternalServerErrorException, UnauthorizedException
from src.utils.http_request import RegexConverter
from src.utils.http_response import HiveApi
from src.utils.sentry_error import init_sentry_hook
from src.utils.auth_token import TokenParser
from src.utils.did.did_init import init_did_backend
from src.utils_v1.constants import HIVE_MODE_PROD, HIVE_MODE_DEV
from src import view

import hive.settings
import hive.main

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')


app = Flask('Hive Node V2')
app.url_map.converters['regex'] = RegexConverter
api = HiveApi(app, prefix='/api/v2')


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

    try:
        TokenParser().parse()
        logging.getLogger('BEFORE REQUEST').info(f'enter {request.full_path}, {request.method}, '
                                                 f'user_did={g.usr_did}, app_did={g.app_did}, app_ins_did={g.app_ins_did}')
    except UnauthorizedException as e:
        return e.get_error_response()
    except HiveException as e:
        return UnauthorizedException(msg=f'TokenParser error: {e.msg}').get_error_response()
    except Exception as e:
        msg = f'Invalid v2 token: {str(e)}, {traceback.format_exc()}'
        logging.getLogger('before_request').error(msg)
        capture_exception(error=Exception(f'V2T UNEXPECTED: {msg}'))
        return UnauthorizedException(msg=msg).get_error_response()


@app.after_request
def after_request(response):
    data_str = str(response.json)
    data_str = data_str[:500] if data_str else ''
    logging.getLogger('AFTER REQUEST').info(f'leave {request.full_path}, {request.method}, status={response.status_code}, data={data_str}')
    return response


def init_log():
    print("init log")
    with open(CONFIG_FILE) as f:
        logging.config.dictConfig(yaml.load(f, Loader=yaml.FullLoader))
    logging.getLogger('file').info("Log in file")
    logging.getLogger('console').info("log in console")
    logging.getLogger('src_init').info("log in console and file")
    logging.info("log in console and file with root Logger")


def create_app(mode=HIVE_MODE_PROD, hive_config='/etc/hive/.env'):
    # init v1 configure items
    hive.settings.hive_setting.init_config(hive_config)

    hive_setting.init_config(hive_config)
    init_log()
    logging.getLogger("src_init").info("##############################")
    logging.getLogger("src_init").info("HIVE NODE IS STARTING")
    logging.getLogger("src_init").info("##############################")
    init_did_backend()

    # init v1 APIs
    hive.main.init_app(app, mode)

    view.init_app(app, api)
    logging.getLogger("src_init").info(f'SENTRY_ENABLED is {hive_setting.SENTRY_ENABLED}.')
    logging.getLogger("src_init").info(f'ENABLE_CORS is {hive_setting.ENABLE_CORS}.')
    if hive_setting.SENTRY_ENABLED and hive_setting.SENTRY_DSN != "":
        init_sentry_hook(hive_setting.SENTRY_DSN)
    if hive_setting.ENABLE_CORS:
        CORS(app, supports_credentials=True)
    return app


def get_docs_app(first=False):
    """
    For sphinx documentation tool to use the flask app to generate the document defined in APIs.

    :param first: first call for initialize app.
    :return: the app of the flask
    """
    if first:
        init_did_backend()
        view.init_app(app, api)
    return app
