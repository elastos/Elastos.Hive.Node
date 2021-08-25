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
        parts = self.hive_setting.HIVE_VERSION.split('.')
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
