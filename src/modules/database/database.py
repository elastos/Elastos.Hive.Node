# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
import json
from bson import json_util

from flask import g

from src.utils.http_request import RequestData
from src.modules.database.mongodb_client import MongodbClient
from src.modules.subscription.vault import VaultManager


class Database:
    def __init__(self):
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()

    def create_collection(self, collection_name):
        """ Create collection by name

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        self.mcli.create_user_collection(g.usr_did, g.app_did, collection_name)
        return {'name': collection_name}

    def delete_collection(self, collection_name):
        """ Delete collection by name

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        self.mcli.delete_user_collection(g.usr_did, g.app_did, collection_name, check_exist=True)

    def __get_collection(self, collection_name):
        return self.mcli.get_user_collection(g.usr_did, g.app_did, collection_name)

    @staticmethod
    def __is_timestamp(options):
        RequestData(options, optional=True).validate_opt('timestamp', bool)
        return options.pop('timestamp', True)

    def insert_document(self, collection_name, documents, options):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        col = self.__get_collection(collection_name)
        return col.insert_many(documents, contains_extra=self.__is_timestamp(options), **options)

    def update_document(self, collection_name, filter_, update, options, is_update_one):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        col = self.__get_collection(collection_name)
        return col.update_many(filter_, update, contains_extra=self.__is_timestamp(options), only_one=is_update_one, **options)

    def delete_document(self, collection_name, col_filter, is_delete_one):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        col = self.__get_collection(collection_name)
        col.delete_many(col_filter, only_one=is_delete_one)

    def count_document(self, collection_name, filter_, options):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        col = self.__get_collection(collection_name)
        return {"count": col.count(filter_, **options)}

    def find_document(self, collection_name, filter_, skip, limit):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        # options is optional
        options = {}
        if skip is not None:
            options['skip'] = skip
        if limit is not None:
            options['limit'] = limit

        return self.__do_internal_find(collection_name, filter_, options)

    def query_document(self, collection_name, filter_, options):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        return self.__do_internal_find(collection_name, filter_, options)

    def __do_internal_find(self, collection_name, filter_, options):
        col = self.__get_collection(collection_name)
        docs = col.find_many(filter_, **options)
        return {"items": [c for c in json.loads(json_util.dumps(docs))]}
