# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src.utils.http_response import hive_restful_response


class About:
    def __init__(self, app, hive_setting):
        self.hive_setting = hive_setting

    @hive_restful_response
    def get_version(self):
        """ This value comes from tag name and must be '***v<major>.<minor>.<patch>' or '<major>.<minor>.<patch>' """
        src = self.hive_setting.HIVE_VERSION
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
            'commit_id': self.hive_setting.HIVE_COMMIT_HASH
        }
