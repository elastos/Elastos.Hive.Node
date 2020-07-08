# -*- coding: utf-8 -*-
import json

from flask import request

from hive.util.auth import did_auth
from hive.util.constants import DID_PREFIX
from hive.util.did_resource import find_schema_of_did_resource, add_did_resource_to_db
from hive.util.server_response import response_ok, response_err


class HiveMongo:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def create_collection(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
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
            return response_err(409, "Collection: " + collection + " exist")

        with self.app.app_context():
            self.app.register_resource(collection, settings)

        data = {"collection": collection}
        return response_ok(data)
