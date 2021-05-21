# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
from hive.util.constants import VAULT_ACCESS_WR, VAULT_ACCESS_DEL
from hive.util.did_mongo_db_resource import get_mongo_database_size
from hive.util.payment.vault_service_manage import update_vault_db_use_storage_byte
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.database_client import cli


class Database:
    def __init__(self):
        pass

    def create_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        cli.create_collection(did, app_did, collection_name)
        return {
            'name': collection_name
        }

    def delete_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_DEL)
        cli.delete_collection(did, app_did, collection_name)
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))

    def insert_document(self, collection_name, json_body):
        pass

    def update_document(self, collection_name, json_body):
        pass

    def delete_document(self, collection_name, json_body):
        pass

    def count_document(self):
        pass

    def find_document(self, collection_name, col_filter, skip, limit):
        pass

    def query_document(self, collection_name, json_body):
        pass
