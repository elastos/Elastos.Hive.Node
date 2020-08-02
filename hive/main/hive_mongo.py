# -*- coding: utf-8 -*-
import json

from flask import request

from hive.main.hive_sync import HiveSync
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.auth import did_auth
from hive.util.constants import DID_RESOURCE_NAME, DID_RESOURCE_SCHEMA, DID, APP_ID
from hive.util.common import gene_eve_mongo_db_prefix
from hive.util.did_info import get_all_did_info
from hive.util.did_mongo_db_resource import find_schema_of_did_resource, add_did_resource_to_db, \
    get_all_resource_of_did_app_id, \
    gene_mongo_db_name
from hive.util.server_response import response_ok, response_err


class HiveMongo:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        self.init_all_eve_from_db()

    def init_all_eve_from_db(self):
        infos = get_all_did_info()
        for info in infos:
            self.init_eve(info[DID], info[APP_ID])

    def create_collection(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        collection = content.get('collection', None)
        schema = content.get('schema', None)
        if (collection is None) or (schema is None):
            return response_err(400, "parameter is null")

        settings = {"schema": schema, "mongo_prefix": gene_eve_mongo_db_prefix(did, app_id)}

        schema_db = find_schema_of_did_resource(did, app_id, collection)
        if schema_db is None:
            add_did_resource_to_db(did, app_id, collection, json.dumps(schema))
        else:
            return response_err(409, "Collection: " + collection + " exist")

        with self.app.app_context():
            self.app.register_resource(collection, settings)

        data = {"collection": collection}
        return response_ok(data)

    def init_eve(self, did, app_id):
        with self.app.app_context():
            uri = gene_eve_mongo_db_prefix(did, app_id) + "_URI"
            if uri not in self.app.config:
                self.app.config[uri] = "mongodb://%s:%s/%s" % (
                    MONGO_HOST,
                    MONGO_PORT,
                    gene_mongo_db_name(did, app_id)
                )
            resource_list = get_all_resource_of_did_app_id(did, app_id)
            for resource in resource_list:
                collection = resource[DID_RESOURCE_NAME]
                schema = resource[DID_RESOURCE_SCHEMA]
                settings = {"schema": json.loads(schema), "mongo_prefix": gene_eve_mongo_db_prefix(did, app_id)}
                if collection not in self.app.config["DOMAIN"]:
                    self.app.register_resource(collection, settings)
