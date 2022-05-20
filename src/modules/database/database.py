# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
import json
from bson import json_util
from datetime import datetime

from flask import g

from src.utils_v1.did_mongo_db_resource import convert_oid, options_filter, populate_find_options_from_body
from src.modules.database.mongodb_client import MongodbClient
from src.modules.subscription.vault import VaultManager, AppSpaceDetector


class Database:
    def __init__(self):
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()

    def create_collection(self, collection_name):
        """ Create collection by name

        :v2 API:
        """
        with AppSpaceDetector(g.usr_did, g.app_did) as vault:
            vault.check_storage()

            self.mcli.create_user_collection(g.usr_did, g.app_did, collection_name)
            return {'name': collection_name}

    def delete_collection(self, collection_name):
        """ Delete collection by name

        :v2 API:
        """
        with AppSpaceDetector(g.usr_did, g.app_did) as _:
            self.mcli.delete_user_collection(g.usr_did, g.app_did, collection_name, check_exist=True)

    def __get_collection(self, collection_name):
        col = self.mcli.get_user_collection(g.usr_did, g.app_did, collection_name)
        return g.usr_did, g.app_did, col.col

    @staticmethod
    def __is_timestamp(json_body):
        return json_body.get('options', {}).get('timestamp') is True

    def insert_document(self, collection_name, json_body):
        """ :v2 API: """
        with AppSpaceDetector(g.usr_did, g.app_did) as vault:
            vault.check_storage()

            user_did, app_did, col = self.__get_collection(collection_name)
            documents = []
            for doc in json_body["document"]:
                if self.__is_timestamp(json_body):
                    doc["created"] = datetime.utcnow()
                    doc["modified"] = datetime.utcnow()
                documents.append(convert_oid(doc))
            ret = col.insert_many(documents, **options_filter(json_body, ("bypass_document_validation", "ordered")))
            return {
                "acknowledged": ret.acknowledged,
                "inserted_ids": [str(_id) for _id in ret.inserted_ids]
            }

    def update_document(self, collection_name, json_body, is_update_one):
        """ :v2 API: """
        with AppSpaceDetector(g.usr_did, g.app_did) as vault:
            vault.check_storage()

            user_did, app_did, col = self.__get_collection(collection_name)
            update = json_body["update"]

            if self.__is_timestamp(json_body):
                if "$set" in update and 'modified' in update['$set']:
                    update["$set"]["modified"] = datetime.utcnow()
                if "$setOnInsert" in update:
                    update["$setOnInsert"]["created"] = datetime.utcnow()
                    update["$setOnInsert"]["modified"] = datetime.utcnow()

            if is_update_one:
                ret = col.update_one(convert_oid(json_body["filter"]), convert_oid(update, update=True),
                                     **options_filter(json_body, ("upsert", "bypass_document_validation")))
            else:
                ret = col.update_many(convert_oid(json_body["filter"]), convert_oid(update, update=True),
                                      **options_filter(json_body, ("upsert", "bypass_document_validation")))

            return {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id) if ret.upserted_id else None
            }

    def delete_document(self, collection_name, col_filter, is_delete_one):
        """ :v2 API: """
        with AppSpaceDetector(g.usr_did, g.app_did) as _:
            user_did, app_did, col = self.__get_collection(collection_name)
            if is_delete_one:
                col.delete_one(convert_oid(col_filter))
            else:
                col.delete_many(convert_oid(col_filter))

    def count_document(self, collection_name, json_body):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        user_did, app_did, col = self.__get_collection(collection_name)
        count = col.count_documents(convert_oid(json_body["filter"] if json_body and 'filter' in json_body else {}),
                                    **options_filter(json_body, ("skip", "limit", "maxTimeMS")))
        return {"count": count}

    def find_document(self, collection_name, col_filter, skip, limit):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        return self.__do_internal_find(collection_name, col_filter, {'skip': skip, 'limit': limit})

    def query_document(self, collection_name, filter_, options):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        return self.__do_internal_find(collection_name, filter_, populate_find_options_from_body(options))

    def __do_internal_find(self, collection_name, col_filter, options):
        user_did, app_did, col = self.__get_collection(collection_name)

        ret = col.find(convert_oid(col_filter if col_filter else {}), **options)
        return {"items": [c for c in json.loads(json_util.dumps(ret))]}
