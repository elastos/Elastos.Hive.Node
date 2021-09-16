# -*- coding: utf-8 -*-

"""
The entrance for ipfs-backup module.
"""
from src.utils.http_response import hive_restful_response


class IpfsBackupClient:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting

    @hive_restful_response
    def get_state(self):
        pass

    @hive_restful_response
    def backup(self, credential):
        pass

    @hive_restful_response
    def restore(self, credential):
        pass


class IpfsBackupServer:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting

    @hive_restful_response
    def promotion(self):
        pass

    @hive_restful_response
    def internal_backup(self):
        pass

    @hive_restful_response
    def internal_backup_state(self):
        pass

    @hive_restful_response
    def internal_restore(self):
        pass
