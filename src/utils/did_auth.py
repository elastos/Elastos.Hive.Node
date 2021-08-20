# -*- coding: utf-8 -*-

"""
Did or auth relating functions.
"""
from src.utils_v1.auth import did_auth, did_auth2
from src.utils.db_client import cli
from src.utils.http_exception import UnauthorizedException


def check_auth():
    did, app_id = did_auth()
    if not did or not app_id:
        raise UnauthorizedException()
    return did, app_id


def check_auth2():
    did, app_id, err = did_auth2()
    if not did:
        raise UnauthorizedException(msg=err)
    return did, app_id


def check_auth_and_vault(permission=None):
    did, app_id = check_auth()
    cli.check_vault_access(did, permission)
    return did, app_id
