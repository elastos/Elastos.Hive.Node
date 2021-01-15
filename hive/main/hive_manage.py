from hive.settings import hive_setting
from hive.util.server_response import ServerResponse

import logging

logger = logging.getLogger("HiveManage")


class HiveManage:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveManage")

    def init_app(self, app):
        self.app = app

    def get_hive_version(self):
        data = {"version": hive_setting.HIVE_VERSION}
        print("version:" + hive_setting.HIVE_VERSION)
        logger.debug("version:" + hive_setting.HIVE_VERSION)
        return self.response.response_ok(data)

    def get_hive_commit_hash(self):
        data = {"commit_hash": hive_setting.HIVE_COMMIT_HASH}
        print("commit_hash:" + hive_setting.HIVE_COMMIT_HASH)
        logger.debug("commit_hash:" + hive_setting.HIVE_COMMIT_HASH)
        return self.response.response_ok(data)
