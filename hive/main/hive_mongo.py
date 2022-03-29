import json
from datetime import datetime

from bson import json_util

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from hive.settings import hive_setting
from hive.util.constants import VAULT_ACCESS_WR, VAULT_ACCESS_R, VAULT_ACCESS_DEL
from hive.util.did_mongo_db_resource import gene_mongo_db_name, options_filter, gene_sort, convert_oid, \
    populate_options_find_many, query_insert_one, query_find_many, populate_options_insert_one, query_count_documents, \
    populate_options_count_documents, query_update_one, populate_options_update_one, query_delete_one, get_collection, \
    get_mongo_database_size
from hive.util.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, NOT_FOUND
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc
from hive.util.payment.vault_service_manage import update_vault_db_use_storage_byte


class HiveMongoDb:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveMongoDb")

    def init_app(self, app):
        self.app = app

    def create_collection(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", access_vault=VAULT_ACCESS_WR)
        if err:
            return err

        collection_name = content.get('collection')

        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URI)

        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]
        try:
            col = db.create_collection(collection_name)
        except CollectionInvalid:
            data = {"existing": True}
            return self.response.response_ok(data)
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))
        return self.response.response_ok()

    def delete_collection(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", access_vault=VAULT_ACCESS_DEL)
        if err:
            return err

        collection_name = content.get('collection', None)
        if collection_name is None:
            return self.response.response_err(BAD_REQUEST, "parameter is null")

        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URI)

        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]
        try:
            db.drop_collection(collection_name)
            db_size = get_mongo_database_size(did, app_id)
            update_vault_db_use_storage_byte(did, db_size)

        except CollectionInvalid:
            pass
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))
        return self.response.response_ok()

    def insert_one(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "document",
                                                             access_vault=VAULT_ACCESS_WR)
        if err:
            return err

        options = populate_options_insert_one(content)

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        data, err_message = query_insert_one(col, content, options)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        db_size = get_mongo_database_size(did, app_id)
        update_vault_db_use_storage_byte(did, db_size)
        return self.response.response_ok(data)

    def insert_many(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "document",
                                                             access_vault=VAULT_ACCESS_WR)

        if err:
            return err

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        options = options_filter(content, ("bypass_document_validation", "ordered"))

        try:
            new_document = []
            for document in content["document"]:
                document["created"] = datetime.utcnow()
                document["modified"] = datetime.utcnow()
                new_document.append(convert_oid(document))

            ret = col.insert_many(new_document, **options)
            db_size = get_mongo_database_size(did, app_id)
            update_vault_db_use_storage_byte(did, db_size)
            data = {
                "acknowledged": ret.acknowledged,
                "inserted_ids": [str(_id) for _id in ret.inserted_ids]
            }
            return self.response.response_ok(data)
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))

    def update_one(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "filter", "update",
                                                             access_vault=VAULT_ACCESS_WR)
        if err:
            return err

        options = populate_options_update_one(content)

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        data, err_message = query_update_one(col, content, options)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        db_size = get_mongo_database_size(did, app_id)
        update_vault_db_use_storage_byte(did, db_size)
        return self.response.response_ok(data)

    def update_many(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "filter", "update",
                                                             access_vault=VAULT_ACCESS_WR)
        if err:
            return err

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        options = options_filter(content, ("upsert", "bypass_document_validation"))

        try:
            update_set_on_insert = content.get('update').get('$setOnInsert', None)
            if update_set_on_insert:
                content["update"]["$setOnInsert"]['created'] = datetime.utcnow()
            else:
                content["update"]["$setOnInsert"] = {
                    "created": datetime.utcnow()
                }
            if "$set" in content["update"]:
                content["update"]["$set"]["modified"] = datetime.utcnow()
            ret = col.update_many(convert_oid(content["filter"]), convert_oid(content["update"], update=True),
                                  **options)
            data = {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id)
            }
            db_size = get_mongo_database_size(did, app_id)
            update_vault_db_use_storage_byte(did, db_size)
            return self.response.response_ok(data)
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))

    def delete_one(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "filter",
                                                             access_vault=VAULT_ACCESS_DEL)
        if err:
            return err

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        data, err_message = query_delete_one(col, content)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        db_size = get_mongo_database_size(did, app_id)
        update_vault_db_use_storage_byte(did, db_size)
        return self.response.response_ok(data)

    def delete_many(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "filter",
                                                             access_vault=VAULT_ACCESS_DEL)
        if err:
            return err

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        try:
            ret = col.delete_many(convert_oid(content["filter"]))
            data = {
                "acknowledged": ret.acknowledged,
                "deleted_count": ret.deleted_count,
            }
            db_size = get_mongo_database_size(did, app_id)
            update_vault_db_use_storage_byte(did, db_size)
            return self.response.response_ok(data)
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))

    def count_documents(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", "filter",
                                                             access_vault=VAULT_ACCESS_R)
        if err:
            return err

        options = populate_options_count_documents(content)

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        data, err_message = query_count_documents(col, content, options)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        return self.response.response_ok(data)

    def find_one(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", access_vault=VAULT_ACCESS_R)
        if err:
            return err

        col = get_collection(did, app_id, content["collection"])
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        options = options_filter(content, ("projection",
                                           "skip",
                                           "sort",
                                           "allow_partial_results",
                                           "return_key",
                                           "show_record_id",
                                           "batch_size"))
        if "sort" in options:
            sorts = gene_sort(options["sort"])
            options["sort"] = sorts

        try:
            if "filter" in content:
                result = col.find_one(convert_oid(content["filter"]), **options)
            else:
                result = col.find_one(**options)

            data = {"items": json.loads(json_util.dumps(result))}
            return self.response.response_ok(data)
        except Exception as e:
            return self.response.response_err(INTERNAL_SERVER_ERROR, "Exception:" + str(e))

    def find_many(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "collection", access_vault=VAULT_ACCESS_R)
        if err:
            return err

        options = populate_options_find_many(content)

        col = get_collection(did, app_id, content.get('collection'))
        if not col:
            return self.response.response_err(NOT_FOUND, "collection not exist")

        data, err_message = query_find_many(col, content, options)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        return self.response.response_ok(data)
