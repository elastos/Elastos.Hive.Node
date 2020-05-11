# -*- coding: utf-8 -*-
import uuid

from eve import Eve, STATUS, STATUS_OK, STATUS_ERR, ETAG
from eve.auth import TokenAuth
from flask import request, jsonify
from pymongo import MongoClient

MONGO_HOST = "localhost"
MONGO_PORT = 27017

DID_PREFIX = "_did_prefix"
DID_DB_PREFIX = "did_of_"
DID_INFO_DB_NAME = "did_info"
DID_INFO_REGISTER_COL = "did_register"

DID_INFO_REGISTER_PASSWORD = "password"
DID_INFO_REGISTER_TOKEN = "token"


class HiveTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        info = get_did_info_by_token(token)
        if info is not None:
            did = info["_id"]
            self.set_mongo_prefix(did + DID_PREFIX)
            return True
        else:
            return False


app = Eve(auth=HiveTokenAuth)


@app.route('/api/v1/echo', methods=['POST'])
def echo():
    # get_json(force=False, silent=False, cache=True)
    # 获取json失败会直接返回
    content = request.get_json()
    return jsonify(content)


def response_ok(data_dic=None):
    ret = {STATUS: STATUS_OK}
    if data_dic is not None:
        ret.update(data_dic)
    return jsonify(ret)


def response_err(code, msg):
    ret = {STATUS: STATUS_ERR}
    ret.update({"_error": {"code": code, "message": msg}})
    return jsonify(ret)


def save_did_info_to_db(did, password):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    did_dic = {"_id": did, DID_INFO_REGISTER_PASSWORD: password, DID_INFO_REGISTER_TOKEN: None}
    i = col.insert_one(did_dic)
    return i


def get_did_info_by_did(did):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {"_id": did}
    info = col.find_one(query)
    return info


def save_token_to_db(did, token):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {"_id": did}
    value = {"$set": {DID_INFO_REGISTER_TOKEN: token}}
    ret = col.update_one(query, value)
    return ret


def get_did_info_by_token(token):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_REGISTER_TOKEN: token}
    info = col.find_one(query)
    return info


def create_token():
    token = uuid.uuid1()
    return str(token)


def did_auth():
    auth = request.headers.get("Authorization").strip()
    if auth.lower().startswith(("token", "bearer")):
        token = auth.split(" ")[1]
        info = get_did_info_by_token(token)
        if info is not None:
            return info["_id"]
        else:
            return None
    else:
        return None


def create_db(did):
    with app.app_context():
        app.config[did + DID_PREFIX + "_URI"] = "mongodb://%s:%s/%s" % (
            MONGO_HOST,
            MONGO_PORT,
            DID_DB_PREFIX + did,
        )
    return did


@app.route('/api/v1/did/register', methods=['POST'])
def did_register():
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


@app.route('/api/v1/did/login', methods=['POST'])
def did_login():
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
    create_db(did)

    token = create_token()
    save_token_to_db(did, token)

    data = {"token": token}
    return response_ok(data)


@app.route('/api/v1/db/create_collection', methods=['POST'])
def create_collection():
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
    with app.app_context():
        app.register_resource(collection, settings)

    data = {"collection": collection}
    return response_ok(data)


if __name__ == '__main__':
    app.run()
