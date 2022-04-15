# -*- coding: utf-8 -*-

"""
Did or auth relating functions.
@deprecated
"""
from src.utils_v1.auth import get_token_info
from src.utils.db_client import cli
from src.utils.http_exception import UnauthorizedException
from src.utils_v1.constants import USER_DID, APP_ID


def __did_auth():
    """ @deprecated """
    info, err = get_token_info()
    did = info[USER_DID] if info else None
    app_did = info[APP_ID] if info and APP_ID in info else None
    return did, app_did, err


def __check_auth2():
    """ @deprecated """
    user_did, app_did, err = __did_auth()
    if not user_did:
        raise UnauthorizedException(msg=err)
    return user_did, app_did


def check_auth_and_vault(permission=None):
    """ @deprecated """
    user_did, app_did = __check_auth2()
    cli.check_vault_access(user_did, permission)
    return user_did, app_did
