# -*- coding: utf-8 -*-

"""
Any database operations can be found here.
"""
import logging
import subprocess

from pymongo.errors import CollectionInvalid

from hive.settings import hive_setting
from pymongo import MongoClient

from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import gene_mongo_db_name, convert_oid, export_mongo_db, get_save_mongo_db_path
from hive.util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_STATE, \
    VAULT_ACCESS_WR, VAULT_ACCESS_DEL, DATETIME_FORMAT, DID, APP_ID
from src.utils.http_exception import NotFoundException, BadRequestException, AlreadyExistsException, \
    VaultNotFoundException, CollectionNotFoundException, ForbiddenException
from datetime import datetime

import os


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
        return self.get_origin_collection(gene_mongo_db_name(did, app_id), collection_name, is_create)

    def get_origin_collection(self, db_name, collection_name, is_create=False):
        db = self.__get_connection()[db_name]
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
            raise VaultNotFoundException()

        if (access_vault == VAULT_ACCESS_WR or access_vault == VAULT_ACCESS_DEL) \
                and info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE:
            raise ForbiddenException(msg="The vault can't be written.")

    def find_many(self, did, app_id, collection_name, col_filter, options):
        col = self.get_user_collection(did, app_id, collection_name)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return list(col.find(convert_oid(col_filter) if col_filter else None, **options))

    def find_one(self, did, app_id, collection_name, col_filter, options=None):
        return self.find_one_origin(gene_mongo_db_name(did, app_id), collection_name, col_filter, options)

    def find_one_origin(self, db_name, collection_name, col_filter, options=None, is_create=False, is_raise=True):
        col = self.get_origin_collection(db_name, collection_name, is_create=is_create)
        if not is_create and not col:
            if not is_raise:
                return None
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return col.find_one(convert_oid(col_filter) if col_filter else None, **(options if options else {}))

    def insert_one(self, did, app_id, collection_name, document, options=None, is_create=False):
        return self.insert_one_origin(gene_mongo_db_name(did, app_id), collection_name, document, options, is_create)

    def insert_one_origin(self, db_name, collection_name, document, options=None, is_create=False):
        col = self.get_origin_collection(db_name, collection_name, is_create)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        document['created'] = datetime.strptime(document["created"], DATETIME_FORMAT) \
            if 'created' in document else datetime.utcnow()
        document['modified'] = datetime.utcnow()

        result = col.insert_one(convert_oid(document), **(options if options else {}))
        return {
            "acknowledged": result.acknowledged,
            "inserted_id": str(result.inserted_id) if result.inserted_id else ''
        }

    def update_one(self, did, app_id, collection_name, col_filter, col_update, options):
        return self.update_one_origin(gene_mongo_db_name(did, app_id), collection_name, col_filter, col_update, options)

    def update_one_origin(self, db_name, collection_name, col_filter, col_update, options=None, is_create=False):
        col = self.get_origin_collection(db_name, collection_name, is_create=is_create)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        if '$setOnInsert' in col_update:
            col_update["$setOnInsert"]['created'] = datetime.utcnow()
        else:
            col_update["$setOnInsert"] = {"created": datetime.utcnow()}
        if "$set" in col_update:
            col_update["$set"]["modified"] = datetime.utcnow()

        result = col.update_one(convert_oid(col_filter), convert_oid(col_update, update=True), **(options if options else {}))
        return {
            "acknowledged": result.acknowledged,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else '',
        }

    def delete_one(self, did, app_id, collection_name, col_filter):
        return self.delete_one_origin(gene_mongo_db_name(did, app_id), collection_name, col_filter)

    def delete_one_origin(self, db_name, collection_name, col_filter, is_check_exist=True):
        col = self.get_origin_collection(db_name, collection_name)
        if not col:
            if is_check_exist:
                raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
            else:
                return {"acknowledged": False, "deleted_count": 0}

        result = col.delete_one(convert_oid(col_filter))
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }

    def stream_to_file(self, stream, file_path):
        try:
            with open(file_path, 'bw') as f:
                chunk_size = 4096
                while True:
                    chunk = stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
            return os.path.getsize(file_path.as_posix())
        except Exception as e:
            raise BadRequestException('Failed to save the file content to local.')

    def create_collection(self, did, app_did, collection_name):
        try:
            self.__get_connection()[gene_mongo_db_name(did, app_did)].create_collection(collection_name)
        except CollectionInvalid as e:
            logging.error('The collection already exists.')
            raise AlreadyExistsException()

    def delete_collection(self, did, app_did, collection_name, is_check_exist=True):
        if is_check_exist and not self.get_user_collection(did, app_did, collection_name):
            raise CollectionNotFoundException()
        self.__get_connection()[gene_mongo_db_name(did, app_did)].drop_collection(collection_name)

    def delete_collection_origin(self, db_name, collection_name):
        if self.get_origin_collection(db_name, collection_name):
            raise CollectionNotFoundException()
        self.__get_connection()[db_name].drop_collection(collection_name)

    def timestamp_to_epoch(self, timestamp):
        if timestamp < 0:
            return timestamp
        t = datetime.fromtimestamp(timestamp)
        s = datetime(1970, 1, 1, 0, 0, 0)
        return int((t - s).total_seconds())

    def export_mongodb(self, did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[DID], did_info[APP_ID])

    def import_mongodb(self, did):
        mongodb_root = get_save_mongo_db_path(did)
        if mongodb_root.exists():
            cmd_line = f'mongorestore -h {self.host} --port {self.port} --drop {mongodb_root}'
            return_code = subprocess.call(cmd_line, shell=True)
            if return_code != 0:
                raise BadRequestException(msg='Failed to restore mongodb data.')


cli = DatabaseClient()


if __name__ == '__main__':
    pass
