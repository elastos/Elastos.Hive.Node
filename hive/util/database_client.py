# -*- coding: utf-8 -*-

"""
Any database operations can be found here.
"""

from hive.settings import hive_setting
from pymongo import MongoClient
from hive.util.did_mongo_db_resource import gene_mongo_db_name, convert_oid
from hive.util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_STATE, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_PRICING_USING, \
    VAULT_ACCESS_WR, DID, APP_ID, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_ACCESS_DEL, DATETIME_FORMAT
from hive.util.http_response import NotFoundException, ErrorCode, BadRequestException
from datetime import datetime


VAULT_SERVICE_FREE = "Free"
VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_FREEZE = "freeze"


class DatabaseClient:
    def __init__(self):
        self.uri = hive_setting.MONGO_URI
        self.host = hive_setting.MONGO_HOST
        self.port = hive_setting.MONGO_PORT

    def __get_connection(self):
        if self.uri:
            connection = MongoClient(self.uri)
        else:
            connection = MongoClient(host=self.host, port=self.port)
        return connection

    def get_user_collection(self, did, app_id, collection_name, is_create=False):
        db = self.__get_connection()[gene_mongo_db_name(did, app_id)]
        if not is_create and collection_name not in db.list_collection_names():
            return None
        return db[collection_name]

    def __get_vault_service(self, did):
        return self.__get_connection()[DID_INFO_DB_NAME][VAULT_SERVICE_COL].find_one({VAULT_SERVICE_DID: did})

    def check_vault_access(self, did, access_vault):
        """
        Check if the vault can be accessed by specific permission
        """
        info = self.__get_vault_service(did)
        if not info:
            raise NotFoundException(msg='The vault does not exist.')

        if (access_vault == VAULT_ACCESS_WR or access_vault == VAULT_ACCESS_DEL)\
                and info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE:
            raise NotFoundException(ErrorCode.VAULT_NO_PERMISSION, "The vault can't be written.")

    def find_many(self, did, app_id, collection_name, col_filter, options):
        col = self.get_user_collection(did, app_id, collection_name)
        if not col:
            raise BadRequestException(msg='Cannot find collection with name ' + collection_name)

        return list(col.find(convert_oid(col_filter) if col_filter else None, **options))

    def insert_one(self, did, app_id, collection_name, document, options):
        col = self.get_user_collection(did, app_id, collection_name)
        if not col:
            raise BadRequestException(msg='Cannot find collection with name ' + collection_name)

        document['created'] = datetime.strptime(document["created"], DATETIME_FORMAT)\
            if 'created' in document else datetime.utcnow()
        document['modified'] = datetime.utcnow()
        ret = col.insert_one(convert_oid(document, **options))

        return {
            "acknowledged": ret.acknowledged,
            "inserted_id": str(ret.inserted_id)
        }


cli = DatabaseClient()


if __name__ == '__main__':
    pass
