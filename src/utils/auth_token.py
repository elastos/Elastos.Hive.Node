# -*- coding: utf-8 -*-
import json
from datetime import datetime

from flask import request, g

from src import UnauthorizedException
from src.modules.auth.user import UserManager
from src.utils.consts import URL_V2, URL_SIGN_IN, URL_AUTH, URL_BACKUP_AUTH, URL_SERVER_INTERNAL_BACKUP, URL_SERVER_INTERNAL_STATE, \
    URL_SERVER_INTERNAL_RESTORE, URL_V1
from src.utils_v1.constants import USER_DID, APP_ID, APP_INSTANCE_DID
from src.modules.auth.auth import Auth
from src.utils.did.did_wrapper import JWT


def __get_token_details(token, is_internal):
    """ check the token is valid JWT string and get the details inside

    :param is_internal: True means request is from other hive node, else is from user
    """
    token_splits = token.split(".")
    if token_splits is None:
        return None, "The token is invalid because of not containing dot!"

    if (len(token_splits) != 3) or token_splits[2] == "":
        return None, "The token is invalid because of containing invalid parts!"

    jwt = JWT.parse(token)
    # check the subject name on /did/auth and /did/backup_auth
    subject = jwt.get_subject()
    if is_internal and subject != "BackupToken":
        return None, "The subject of the token for internal is invalid!"
    if not is_internal and subject != "AccessToken":
        return None, "The subject of the token is invalid!"

    issuer = jwt.get_issuer()
    if issuer != Auth().get_did_string():
        return None, "The issuer of the token is invalid!"

    if datetime.now().timestamp() > float(jwt.get_expiration()):
        return None, "Then token is expired!"

    props_json = json.loads(jwt.get_claim('props'))
    if USER_DID not in props_json:
        return None, 'The token MUST contain user DID'

    # There is no application DID in the internal token
    if not is_internal and APP_ID not in props_json:
        return None, 'The token MUST contain application DID'

    props_json[APP_INSTANCE_DID] = jwt.get_audience()
    return props_json, None


def _get_token_details_from_header(is_internal=False):
    """ Make sure the token in header is valid string """
    author = request.headers.get("Authorization")
    if author is None:
        return None, "Can't find the Authorization!"

    if not author.strip().lower().startswith(("token", "bearer")):
        return None, "Can't find the token with prefix token or bearer!"

    auth_splits = author.split(" ")
    if len(auth_splits) < 2:
        return None, "Can't find the token value!"

    access_token = auth_splits[1]
    if not access_token:
        return None, "The token is empty!"

    return __get_token_details(access_token, is_internal=is_internal)


def try_to_get_info_for_v1_token():
    """ used for v1 APIs to later usage, do not need verify token here
    Skip if failed

    g.usr_did: to update vault database usage

    """

    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.strip().lower().startswith(("token", "bearer")):
            return

        parts = authorization.split(' ')
        if len(parts) < 2 or not parts[1]:
            return

        jwt = JWT.parse(parts[1])
        props_json = json.loads(jwt.get_claim('props'))
        if not props_json.get(USER_DID, None):
            return

        g.usr_did = props_json[USER_DID]
    except Exception as e:
        ...


class TokenParser:
    EXCEPT_URLS = ['/api/v2/about/version', '/api/v2/node/version', '/api/v2/about/commit_id', '/api/v2/node/commit_id',
                   URL_V2 + URL_SIGN_IN, URL_V2 + URL_AUTH, URL_V2 + URL_BACKUP_AUTH]
    INTERNAL_URLS = [URL_V2 + URL_SERVER_INTERNAL_BACKUP, URL_V2 + URL_SERVER_INTERNAL_STATE, URL_V2 + URL_SERVER_INTERNAL_RESTORE]
    SCRIPTING_PREFIX = URL_V2 + '/vault/scripting'

    def __init__(self):
        """ Parse the token from the request header if exists and set the following items:
        1. g.usr_did
        2. g.app_did
        3. g.app_ins_did

        the implementation of all APIs can directly use this two global variables.
        """
        g.usr_did, g.app_did, g.app_ins_did = None, None, None
        self.user_manager = UserManager()

    def __no_need_auth(self):
        return any(map(lambda url: request.full_path.startswith(url), self.EXCEPT_URLS))

    def __script_anonymous_request(self):
        # if the request is for scripting service
        if not request.full_path.startswith(self.SCRIPTING_PREFIX):
            return False

        # upload or download by transaction id
        if request.full_path.startswith(URL_V2 + '/vault/scripting/stream/') \
                and request.method.upper() in ['PUT', 'GET']:
            return True

        # call script or call script by only url
        if request.full_path.startswith(URL_V2 + '/vault/scripting') \
                and request.method.upper() in ['PATCH', 'GET']:
            return True

        return False

    def record_user_did_and_app_did(self, user_did, app_did):
        """ Just for cached token in app side to

        @deprecated this will be commented many days later
        """
        self.user_manager.add_app_if_not_exists(user_did, app_did)

    def parse(self):
        """ Only handle the access token of v2 APIs.
        The token for v1 APIs will be checked on related request handler.
        """
        if request.full_path.startswith(URL_V1):
            try_to_get_info_for_v1_token()
            return
        elif not request.full_path.startswith(URL_V2) or self.__no_need_auth():
            return

        # v2 and need handle token

        # The scripting support anonymous running the script when two anonymous options are True
        # So here is just do some checking about token, and record the error on g object
        # In real request handling, it will check if the token is required (g.token_error not None).
        if self.__script_anonymous_request():
            info, err = _get_token_details_from_header()
            g.usr_did = g.app_ins_did = g.app_did = g.token_error = None  # Set the attributes to g.
            if err is not None:
                g.token_error = err
                return

            g.usr_did, g.app_ins_did, g.app_did = info[USER_DID], info[APP_INSTANCE_DID], info[APP_ID]
            self.record_user_did_and_app_did(g.usr_did, g.app_did)
            return

        # Access token has two types: normal from user, internal (for backup) from other hive nodes.
        is_internal = any(map(lambda url: request.full_path.startswith(url), self.INTERNAL_URLS))
        info, err = _get_token_details_from_header(is_internal=is_internal)
        if err is not None:
            raise UnauthorizedException(f'Parse access token error: {err}')

        # Only normal token contains application DID.
        g.usr_did, g.app_ins_did, g.app_did = info[USER_DID], info[APP_INSTANCE_DID], info.get(APP_ID)
        self.record_user_did_and_app_did(g.usr_did, g.app_did)
