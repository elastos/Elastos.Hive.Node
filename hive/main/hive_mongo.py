# -*- coding: utf-8 -*-
import json

from flask import request

from hive.util.auth import did_auth
from hive.util.constants import DID_PREFIX, DID_DB_PREFIX, DID_INFO_REGISTER_PASSWORD, DID_RESOURCE_NAME, \
    DID_RESOURCE_SCHEMA
from hive.util.did_info import add_did_info_to_db, get_did_info_by_did, save_token_to_db, create_token
from hive.util.did_resource import get_all_resource_of_did, find_schema_of_did_resource, add_did_resource_to_db, \
    update_schema_of_did_resource
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
            resource_list = get_all_resource_of_did(did)
            for resource in resource_list:
                collection = resource[DID_RESOURCE_NAME]
                schema = resource[DID_RESOURCE_SCHEMA]
                settings = {"schema": json.loads(schema), "mongo_prefix": did + DID_PREFIX}
                self.app.register_resource(collection, settings)

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
            add_did_info_to_db(did, password)
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

        schema_db = find_schema_of_did_resource(did, collection)
        if schema_db is None:
            add_did_resource_to_db(did, collection, json.dumps(schema))
        else:
            # If allow a collection with same name in db of this did,
            # should add list and delete(drop collection) function
            # temporarily not support
            return response_err(409, "Collection: "+collection+" exist")

        with self.app.app_context():
            self.app.register_resource(collection, settings)

        data = {"collection": collection}
        return response_ok(data)
