from datetime import datetime

from bson import ObjectId

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import DATETIME_FORMAT
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, options_filter, gene_sort
from hive.util.server_response import response_ok, response_err
from hive.main.interceptor import post_json_param_pre_proc


class HiveMongoDb:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def create_collection(self):
        did, app_id, content, response = post_json_param_pre_proc("collection")
        if content is None:
            return response

        collection_name = content.get('collection', None)
        if collection_name is None:
            return response_err(400, "parameter is null")

        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]
        try:
            col = db.create_collection(collection_name)
        except CollectionInvalid:
            pass
        except Exception as e:
            return response_err(500, "Exception:" + str(e))
        return response_ok()

    def delete_collection(self):
        did, app_id, content, response = post_json_param_pre_proc("collection")
        if content is None:
            return response

        collection_name = content.get('collection', None)
        if collection_name is None:
            return response_err(400, "parameter is null")

        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]
        try:
            db.drop_collection(collection_name)
        except CollectionInvalid:
            pass
        except Exception as e:
            return response_err(500, "Exception:" + str(e))
        return response_ok()

    def insert_one(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "document")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        options = options_filter(content, ("bypass_document_validation",))
        try:
            content["document"]["created"] = datetime.utcnow()
            content["document"]["modified"] = datetime.utcnow()
            ret = col.insert_one(content["document"], **options)

            data = {
                "acknowledged": ret.acknowledged,
                "inserted_id": str(ret.inserted_id)
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def insert_many(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "document")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])

        options = options_filter(content, ("bypass_document_validation", "ordered"))

        try:
            for document in content["document"]:
                document["created"] = datetime.utcnow()
                document["modified"] = datetime.utcnow()
            ret = col.insert_many(content["document"], **options)
            data = {
                "acknowledged": ret.acknowledged,
                "inserted_ids": [str(_id) for _id in ret.inserted_ids]
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def update_one(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "filter", "update")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        options = options_filter(content, ("upsert", "bypass_document_validation"))

        try:
            content["update"]["$setOnInsert"] = {
                "created": datetime.utcnow()
            }
            content["filter"]["modified"] = datetime.utcnow()
            ret = col.update_one(content["filter"], content["update"], **options)
            data = {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id),
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def update_many(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "filter", "update")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        options = options_filter(content, ("upsert", "bypass_document_validation"))

        try:
            content["update"]["$setOnInsert"] = {
                "created": datetime.utcnow()
            }
            content["filter"]["modified"] = datetime.utcnow()
            ret = col.update_many(content["filter"], content["update"], **options)
            data = {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id)
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def delete_one(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "filter")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        try:
            ret = col.delete_one(content["filter"])
            data = {
                "acknowledged": ret.acknowledged,
                "deleted_count": ret.deleted_count,
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def delete_many(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "filter")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        try:
            ret = col.delete_many(content["filter"])
            data = {
                "acknowledged": ret.acknowledged,
                "deleted_count": ret.deleted_count,
            }
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def count_documents(self):
        did, app_id, content, response = post_json_param_pre_proc("collection", "filter")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])

        options = options_filter(content, ("skip", "limit", "maxTimeMS"))

        try:
            count = col.count_documents(content["filter"], **options)
            data = {"count": count}
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def find_one(self):
        did, app_id, content, response = post_json_param_pre_proc("collection")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])
        options = options_filter(content, ("filter",
                                           "projection",
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
            result = col.find_one(**options)
            if ("_id" in result) and (isinstance(result["_id"], ObjectId)):
                result["_id"] = str(result["_id"])
            data = {"items": result}
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

    def find_many(self):
        did, app_id, content, response = post_json_param_pre_proc("collection")
        if content is None:
            return response

        col = get_collection(did, app_id, content["collection"])

        options = options_filter(content, ("filter",
                                           "projection",
                                           "skip",
                                           "limit",
                                           "sort",
                                           "allow_partial_results",
                                           "return_key",
                                           "show_record_id",
                                           "batch_size"))
        if "sort" in options:
            sorts = gene_sort(options["sort"])
            options["sort"] = sorts

        try:
            cursor = col.find(**options)
            arr = list()
            for c in cursor:
                if ("_id" in c) and (isinstance(c["_id"], ObjectId)):
                    c["_id"] = str(c["_id"])
                arr.append(c)
            data = {"items": arr}
            return response_ok(data)
        except Exception as e:
            return response_err(500, "Exception:" + str(e))
