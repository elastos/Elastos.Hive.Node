# -*- coding: utf-8 -*-

"""
The view of authentication module.
"""
from flask import Blueprint
from src.modules.auth.auth import Auth
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params

from src.utils.consts import URL_DID_SIGN_IN, URL_DID_AUTH, URL_DID_BACKUP_AUTH

blueprint = Blueprint('auth', __name__)
auth: Auth = Auth()


def init_app(app):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route(URL_DID_SIGN_IN, methods=['POST'])
def did_sign_in():
    """ Sign in with the application DID and get the challenge string.

    .. :quickref: 01 Authentication; Sign in with app DID

    **Request**:

    .. code-block:: json

        {
            "id": "<the user’s did_document>",
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
           “challenge”: “<the authentication challenge encoded in JWT>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    """
    doc, msg = params.get_dict('id')
    if msg or not doc:
        return InvalidParameterException().get_error_response()
    return auth.sign_in(doc)


@blueprint.route(URL_DID_AUTH, methods=['POST'])
def did_auth():
    """ Auth to get the access token for the user DID and the application DID.

    .. :quickref: 01 Authentication; Get the access token.

    **Request**:

    .. code-block:: json

        {
            "challenge_response": "<the response for the authentication challenge encoded in JWT>",
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
            “token”: “<the access token encoded in JWT>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    """
    challenge_response, msg = params.get_str('challenge_response')
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    return auth.auth(challenge_response)


@blueprint.route(URL_DID_BACKUP_AUTH, methods=['POST'])
def backup_auth():
    """ Get the access token for the vault service node. """
    challenge_response, msg = params.get_str('challenge_response')
    if msg or not challenge_response:
        return InvalidParameterException().get_error_response()
    return auth.backup_auth(challenge_response)
