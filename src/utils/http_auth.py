# -*- coding: utf-8 -*-
from hive.util.auth import did_auth
from src import UnauthorizedException


def check_auth():
    """
    TODO: to be moved to other place.
    """
    did, app_id = did_auth()
    if not did or not app_id:
        raise UnauthorizedException()
    return did, app_id
