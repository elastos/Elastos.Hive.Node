# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
from hive.util.constants import VAULT_ACCESS_WR, VAULT_ACCESS_DEL
from hive.util.did_mongo_db_resource import get_mongo_database_size
from hive.util.payment.vault_service_manage import update_vault_db_use_storage_byte
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.database_client import cli
from src.utils.http_response import hive_restful_response, hive_restful_code_response


class Database:
    def __init__(self):
        pass

    @hive_restful_code_response
    def create_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        return {'name': collection_name}, 201 if cli.create_collection(did, app_did, collection_name) else 200

    @hive_restful_response
    def delete_collection(self, collection_name):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_DEL)
        cli.delete_collection(did, app_did, collection_name, is_check_exist=False)
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_did))

    @hive_restful_response
    def insert_document(self, collection_name, json_body):
        pass

    def update_document(self, collection_name, json_body):
        pass

    def delete_document(self, collection_name, json_body):
        pass

    def count_document(self, collection_name):
        pass

    def find_document(self, collection_name, col_filter, skip, limit):
        pass

    def query_document(self, collection_name, json_body):
        pass
