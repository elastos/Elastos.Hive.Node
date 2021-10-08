# -*- coding: utf-8 -*-

"""
Did or auth relating functions.
"""
from src.utils_v1.auth import did_auth, did_auth2
from src.utils.db_client import cli
from src.utils.http_exception import UnauthorizedException


def check_auth():
    user_did, app_id = did_auth()
    if not user_did or not app_id:
        raise UnauthorizedException()
    return user_did, app_id


def check_auth2():
    user_did, app_id, err = did_auth2()
    if not user_did:
        raise UnauthorizedException(msg=err)
    return user_did, app_id


def check_auth_and_vault(permission=None):
    user_did, app_id = check_auth()
    cli.check_vault_access(user_did, permission)
    return user_did, app_id
