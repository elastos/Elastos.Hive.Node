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
        data = {"version": hive_setting.VERSION}
        print("version:" + hive_setting.VERSION)
        logger.debug("version:" + hive_setting.VERSION)
        return self.response.response_ok(data)

    def get_hive_commit_hash(self):
        data = {"commit_hash": hive_setting.LAST_COMMIT}
        print("commit_hash:" + hive_setting.LAST_COMMIT)
        logger.debug("commit_hash:" + hive_setting.LAST_COMMIT)
        return self.response.response_ok(data)
