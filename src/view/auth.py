# -*- coding: utf-8 -*-

"""
The view of authentication module.
"""
from flask_restful import Resource

from src.modules.auth import auth
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params


class SignIn(Resource):
    def __init__(self):
        self.auth = auth.Auth()

    def post(self):
        """ Sign in with the application instance DID to get the challenge string.

        .. :quickref: 01 Authentication; Sign in with app instance DID

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
            raise InvalidParameterException()
        return self.auth.sign_in(doc)


class Auth(Resource):
    def __init__(self):
        self.auth = auth.Auth()

    def post(self):
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
            raise InvalidParameterException(msg=msg)
        return self.auth.auth(challenge_response)


class BackupAuth(Resource):
    def __init__(self):
        self.auth = auth.Auth()

    def post(self):
        """ Get the access token for the vault service node. """
        challenge_response, msg = params.get_str('challenge_response')
        if msg or not challenge_response:
            raise InvalidParameterException()
        return self.auth.backup_auth(challenge_response)
