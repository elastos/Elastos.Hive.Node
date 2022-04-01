# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src import hive_setting
from src.modules.provider.provider import Provider
from src.utils.http_response import hive_restful_response
from src.utils_v1.auth import get_auth


class About:
    def __init__(self):
        pass

    @hive_restful_response
    def get_version(self):
        """ This value comes from tag name and must be '***v<major>.<minor>.<patch>' or '<major>.<minor>.<patch>' """
        src = hive_setting.VERSION
        index = src.rfind('v')
        if index >= 0:
            src = src[index + 1:]
        parts = src.split('.')
        return {
            'major': int(parts[0]),
            'minor': int(parts[1]),
            'patch': int(parts[2]),
        }

    @hive_restful_response
    def get_commit_id(self):
        return {
            'commit_id': hive_setting.LAST_COMMIT
        }

    @hive_restful_response
    def get_node_info(self):
        owner_did, credential = Provider.get_verified_owner_did()
        auth = get_auth()
        return {
            "service_did": auth.did_str,
            "owner_did": owner_did,
            "ownership_presentation": auth.get_ownership_presentation(credential),
            "name": hive_setting.NODE_NAME,
            "email": hive_setting.NODE_EMAIL,
            "description": hive_setting.NODE_DESCRIPTION,
            "version": hive_setting.VERSION,
            "last_commit_id": hive_setting.LAST_COMMIT
        }
