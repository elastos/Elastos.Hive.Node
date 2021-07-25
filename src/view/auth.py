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
    """ Sign in with the application DID and get the challenge string.

    .. :quickref: Authentication; Sign in with app DID

    **Request**:

    .. sourcecode:: http

        {
            "id": "<the user’s did_document>",
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 OK

        {
           “challenge”: “<the authentication challenge encoded in JWT>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    """
    return auth.sign_in(params.get('id'))


@blueprint.route(URL_DID_AUTH, methods=['POST'])
def did_auth():
    """ Auth to get the access token for the user DID and the application DID.

    .. :quickref: Authentication; Get the access token.

    **Request**:

    .. sourcecode:: http

        {
            "challenge_response": "<the response for the authentication challenge encoded in JWT>",
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 OK

        {
               “token”: “<the access token encoded in JWT>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    """
    return auth.auth(params.get('challenge_response'))


@blueprint.route(URL_DID_BACKUP_AUTH, methods=['POST'])
def backup_auth():
    """ Get the access token for the vault service node. """
    return auth.backup_auth(params.get('challenge_response'))
