# -*- coding: utf-8 -*-

from flask import request

from hive.util.auth import did_auth
from hive.util.constants import DID_PREFIX, DID_DB_PREFIX, DID_INFO_REGISTER_PASSWORD
from hive.util.did_info import save_did_info_to_db, get_did_info_by_did, save_token_to_db, create_token
from hive.util.server_response import response_ok, response_err
from hive.settings import MONGO_HOST, MONGO_PORT


class HiveMongo:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def create_db(self, did):
        with self.app.app_context():
            self.app.config[did + DID_PREFIX + "_URI"] = "mongodb://%s:%s/%s" % (
                MONGO_HOST,
                MONGO_PORT,
                DID_DB_PREFIX + did,
            )
        return did

    def did_register(self):
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        did = content.get('did', None)
        password = content.get('password', None)
        if (did is None) or (password is None):
            return response_err(400, "parameter is null")

        try:
            save_did_info_to_db(did, password)
        except Exception as e:
            print("Exception in did_register::", e)

        return response_ok()

    def did_login(self):
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        did = content.get('did', None)
        password = content.get('password', None)
        if (did is None) or (password is None):
            return response_err(400, "parameter is null")

        info = get_did_info_by_did(did)
        if info is None:
            return response_err(401, "User error")

        # verify password
        pw = info[DID_INFO_REGISTER_PASSWORD]
        if password != pw:
            return response_err(401, "Password error")

        # todo 加入到初始化模块,从数据获取信息create_db
        self.create_db(did)

        token = create_token()
        save_token_to_db(did, token)

        data = {"token": token}
        return response_ok(data)

    def create_collection(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        collection = content.get('collection', None)
        schema = content.get('schema', None)
        if (collection is None) or (schema is None):
            return response_err(400, "parameter is null")

        settings = {"schema": schema, "mongo_prefix": did + DID_PREFIX}

        # todo 创建成功后需要加入初始化模块,启动服务的时候或者用户登录的时候从数据库获取schema信息register_resource
        with self.app.app_context():
            self.app.register_resource(collection, settings)

        data = {"collection": collection}
        return response_ok(data)
