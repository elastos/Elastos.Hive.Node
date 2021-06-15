# -*- coding: utf-8 -*-

"""
The view of authentication module.
"""
from flask import Blueprint
from src.modules.auth.auth import Auth
from src.utils.http_request import params

from src.utils.consts import URL_DID_SIGN_IN, URL_DID_AUTH, URL_DID_BACKUP_AUTH

blueprint = Blueprint('auth', __name__)
auth: Auth = None


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global auth
    auth = Auth(app, hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route(URL_DID_SIGN_IN, methods=['POST'])
def did_sign_in():
    return auth.sign_in(params.get('id'))


@blueprint.route(URL_DID_AUTH, methods=['POST'])
def did_auth():
    return auth.auth(params.get('challenge_response'))


@blueprint.route(URL_DID_BACKUP_AUTH, methods=['POST'])
def backup_auth():
    return auth.backup_auth(params.get('challenge_response'))
