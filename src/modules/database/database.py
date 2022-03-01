# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
import json
from datetime import datetime

from bson import json_util

from src.utils_v1.constants import VAULT_ACCESS_WR, VAULT_ACCESS_DEL, VAULT_ACCESS_R
from src.utils_v1.did_mongo_db_resource import get_mongo_database_size, convert_oid, options_filter
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_mongodb_data
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.http_exception import BadRequestException, CollectionNotFoundException, InvalidParameterException
from src.utils.http_response import hive_restful_response


class Database:
    def __init__(self):
        pass

    @hive_restful_response
    def create_collection(self, collection_name):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        cli.create_collection(user_did, app_did, collection_name)
        return {'name': collection_name}

    @hive_restful_response
    def delete_collection(self, collection_name):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_DEL)
        cli.delete_collection(user_did, app_did, collection_name, is_check_exist=False)
        update_used_storage_for_mongodb_data(user_did, get_mongo_database_size(user_did, app_did))

    def __get_collection(self, collection_name, vault_permission):
        user_did, app_did = check_auth_and_vault(vault_permission)
        col = cli.get_user_collection(user_did, app_did, collection_name)
        if not col:
            raise CollectionNotFoundException(msg=f'The collection {collection_name} can not be found.')
        return user_did, app_did, col

    @hive_restful_response
    def insert_document(self, collection_name, json_body):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)
        documents = []
        for document in json_body["document"]:
            document["created"] = datetime.utcnow()
            document["modified"] = datetime.utcnow()
            documents.append(convert_oid(document))
        ret = col.insert_many(documents, **options_filter(json_body, ("bypass_document_validation", "ordered")))
        update_used_storage_for_mongodb_data(user_did, get_mongo_database_size(user_did, app_did))
        return {
            "acknowledged": ret.acknowledged,
            "inserted_ids": [str(_id) for _id in ret.inserted_ids]
        }

    @hive_restful_response
    def update_document(self, collection_name, json_body, is_update_one):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)
        update = json_body["update"]
        if "$set" in update:
            update["$set"]["modified"] = datetime.utcnow()
        if is_update_one:
            ret = col.update_one(convert_oid(json_body["filter"]), convert_oid(update, update=True),
                                 **options_filter(json_body, ("upsert", "bypass_document_validation")))
        else:
            ret = col.update_many(convert_oid(json_body["filter"]), convert_oid(update, update=True),
                                  **options_filter(json_body, ("upsert", "bypass_document_validation")))

        update_used_storage_for_mongodb_data(user_did, get_mongo_database_size(user_did, app_did))
        return {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id) if ret.upserted_id else None
        }

    @hive_restful_response
    def delete_document(self, collection_name, col_filter, is_delete_one):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)
        if is_delete_one:
            col.delete_one(convert_oid(col_filter))
        else:
            col.delete_many(convert_oid(col_filter))
        update_used_storage_for_mongodb_data(user_did, get_mongo_database_size(user_did, app_did))

    @hive_restful_response
    def count_document(self, collection_name, json_body):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_R)
        count = col.count_documents(convert_oid(json_body["filter"] if json_body and 'filter' in json_body else {}),
                                    **options_filter(json_body, ("skip", "limit", "maxTimeMS")))
        return {"count": count}

    @hive_restful_response
    def find_document(self, collection_name, col_filter, skip, limit):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_R)
        return self.__do_find(col, col_filter, {'skip': skip, 'limit': limit})

    @hive_restful_response
    def query_document(self, collection_name, json_body):
        user_did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)
        return self.__do_find(col, json_body.get('filter'),
                              options_filter(json_body, ("projection",
                                                         "skip",
                                                         "limit",
                                                         "sort",
                                                         "allow_partial_results",
                                                         "return_key",
                                                         "show_record_id",
                                                         "batch_size")))

    def __do_find(self, col, col_filter, options):
        ret = col.find(convert_oid(col_filter if col_filter else {}), **options)
        return {"items": [c for c in json.loads(json_util.dumps(ret))]}
