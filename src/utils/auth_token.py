# -*- coding: utf-8 -*-
import json
from datetime import datetime

from flask import request, g

from src import UnauthorizedException
from src.utils.consts import URL_V2, URL_SIGN_IN, URL_AUTH, URL_BACKUP_AUTH, URL_SERVER_INTERNAL_BACKUP, URL_SERVER_INTERNAL_STATE, URL_SERVER_INTERNAL_RESTORE
from src.utils_v1.constants import USER_DID, APP_ID, APP_INSTANCE_DID
from src.modules.auth.auth import Auth
from src.utils.did.did_wrapper import JWT


def __get_info_from_token(token):
    token_splits = token.split(".")
    if token_splits is None:
        return None, "Then token is invalid because of not containing dot!"

    if (len(token_splits) != 3) or token_splits[2] == "":
        return None, "Then token is invalid because of containing invalid parts!"

    jwt = JWT.parse(token)
    issuer = jwt.get_issuer()
    if issuer != Auth().get_did_string():
        return None, "The issuer is invalid!"

    if int(datetime.now().timestamp()) > jwt.get_expiration():
        return None, "Then token is expired!"

    props_json = json.loads(jwt.get_claim('props'))
    if USER_DID not in props_json:
        return None, 'The token must contains user DID'
    props_json[APP_INSTANCE_DID] = jwt.get_audience()
    return props_json, None


def _get_token_info():
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

    return __get_info_from_token(access_token)


class TokenParser:
    except_urls = ['/api/v2/about/version', '/api/v2/node/version', '/api/v2/about/commit_id', '/api/v2/node/commit_id',
                   URL_V2 + URL_SIGN_IN, URL_V2 + URL_AUTH, URL_V2 + URL_BACKUP_AUTH]
    internal_urls = [URL_V2 + URL_SERVER_INTERNAL_BACKUP, URL_V2 + URL_SERVER_INTERNAL_STATE, URL_V2 + URL_SERVER_INTERNAL_RESTORE]

    def __init__(self):
        """ Parse the token from the request header if exists and set the following items:
        1. g.usr_did
        2. g.app_did
        3. g.app_ins_did

        the implementation of all APIs can directly use this two global variables.
        """
        g.usr_did, g.app_did, g.app_ins_did = None, None, None

    def __no_need_auth(self):
        return any(map(lambda url: request.full_path.startswith(url), self.except_urls))

    def __internal_request(self):
        return any(map(lambda url: request.full_path.startswith(url), self.internal_urls))

    def parse(self):
        if not request.full_path.startswith('/api/v2') or self.__no_need_auth():
            return

        info, err = _get_token_info()
        if err:
            raise UnauthorizedException(msg=f'Parse token error: {err}')

        g.usr_did, g.app_ins_did = info[USER_DID], info[APP_INSTANCE_DID]
        if self.__internal_request():
            return

        if APP_ID not in info:
            return None, 'The token must contains application DID'
        g.app_did = info[APP_ID]
