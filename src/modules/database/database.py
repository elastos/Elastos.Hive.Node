# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
import json
from datetime import datetime

from bson import json_util

from hive.util.constants import VAULT_ACCESS_WR, VAULT_ACCESS_DEL, VAULT_ACCESS_R
from hive.util.did_mongo_db_resource import get_mongo_database_size, convert_oid, options_filter
from hive.util.payment.vault_service_manage import update_vault_db_use_storage_byte
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.db_client import cli
from src.utils.http_exception import BadRequestException, CollectionNotFoundException
from src.utils.http_response import hive_restful_response


class Database:
    def __init__(self):
        pass

    @hive_restful_response
    def create_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        cli.create_collection(did, app_did, collection_name)
        return {'name': collection_name}

    @hive_restful_response
    def delete_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_DEL)
        cli.delete_collection(did, app_did, collection_name, is_check_exist=False)
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))

    def __get_collection(self, collection_name, vault_permission):
        did, app_did = check_auth_and_vault(vault_permission)
        col = cli.get_user_collection(did, app_did, collection_name)
        if not col:
            raise CollectionNotFoundException(msg=f'The collection {collection_name} does not found.')
        return did, app_did, col

    @hive_restful_response
    def insert_document(self, collection_name, json_body):
        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)

        if not json_body:
            raise BadRequestException(msg='Invalid parameter.')
        if type(json_body.get('document')) not in (list, tuple):
            raise BadRequestException(msg='Invalid parameter document.')

        documents = []
        for document in json_body["document"]:
            document["created"] = datetime.utcnow()
            document["modified"] = datetime.utcnow()
            documents.append(convert_oid(document))
        ret = col.insert_many(documents, **options_filter(json_body, ("bypass_document_validation", "ordered")))
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))
        return {
            "acknowledged": ret.acknowledged,
            "inserted_ids": [str(_id) for _id in ret.inserted_ids]
        }

    @hive_restful_response
    def update_document(self, collection_name, json_body):
        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)

        if 'filter' in json_body and type(json_body.get('filter')) is not dict:
            raise BadRequestException(msg='Invalid parameter filter.')
        if type(json_body.get('update')) is not dict:
            raise BadRequestException(msg='Invalid parameter update.')

        update = json_body["update"]
        if "$set" in update:
            update["$set"]["modified"] = datetime.utcnow()
        ret = col.update_many(convert_oid(json_body["filter"]), convert_oid(update, update=True),
                              **options_filter(json_body, ("upsert", "bypass_document_validation")))

        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))
        return {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id) if ret.upserted_id else None
        }

    @hive_restful_response
    def delete_document(self, collection_name, json_body):
        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)

        if json_body and 'filter' in json_body and type(json_body.get('filter')) is not dict:
            raise BadRequestException(msg='Invalid parameter filter.')

        col.delete_many(convert_oid(json_body["filter"] if json_body and 'filter' in json_body else {}))
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))

    @hive_restful_response
    def count_document(self, collection_name, json_body):
        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_R)

        if json_body and 'filter' in json_body and type(json_body.get('filter')) is not dict:
            raise BadRequestException(msg='Invalid parameter filter.')

        count = col.count_documents(convert_oid(json_body["filter"] if json_body and 'filter' in json_body else {}),
                                    **options_filter(json_body, ("skip", "limit", "maxTimeMS")))
        return {"count": count}

    @hive_restful_response
    def find_document(self, collection_name, col_filter, skip, limit):
        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_R)

        col_filter = json.loads(col_filter) if col_filter else {}
        if col_filter and type(col_filter) is not dict:
            raise BadRequestException(msg='Invalid parameter filter.')

        options = dict()
        options['skip'] = self.__get_int_by_str(skip)
        options['limit'] = self.__get_int_by_str(limit)
        return self.__do_find(col, col_filter, options)

    def __get_int_by_str(self, s, default=0):
        if s:
            try:
                return int(s)
            except ValueError:
                pass
        return default

    @hive_restful_response
    def query_document(self, collection_name, json_body):
        if not json_body or not collection_name:
            raise BadRequestException(msg='Request body empty or not collection name.')

        did, app_did, col = self.__get_collection(collection_name, VAULT_ACCESS_WR)

        if 'filter' in json_body and type(json_body.get('filter')) is not dict:
            raise BadRequestException(msg='Invalid parameter filter.')

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
