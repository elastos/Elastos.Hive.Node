from settings import HIVE_VERSION, HIVE_COMMIT_HASH
from util.server_response import ServerResponse


class HiveManage:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveManage")

    def init_app(self, app):
        self.app = app

    def get_hive_version(self):
        data = {"version": HIVE_VERSION}
        return self.response.response_ok(data)

    def get_hive_commit_hash(self):
        data = {"commit_hash": HIVE_COMMIT_HASH}
        return self.response.response_ok(data)
