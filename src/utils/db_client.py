# -*- coding: utf-8 -*-

"""
Any database operations can be found here.
"""
import os
import logging
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from src.settings import hive_setting
from src.utils.consts import get_unique_dict_item_from_list
from src.utils_v1.did_mongo_db_resource import gene_mongo_db_name, convert_oid, get_user_database_prefix
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, USER_DID, APP_ID, DID_INFO_REGISTER_COL, APP_INSTANCE_DID
from src.utils.http_exception import BadRequestException, AlreadyExistsException, VaultNotFoundException, CollectionNotFoundException

VAULT_SERVICE_FREE = "Free"
VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_FREEZE = "freeze"


class DatabaseClient:
    def __init__(self):
        self.mongodb_uri = hive_setting.MONGODB_URI
        self.connection = None

    def __get_connection(self):
        if not self.connection:
            self.connection = MongoClient(self.mongodb_uri)
        return self.connection

    def start_session(self):
        return self.__get_connection().start_session()

    def is_database_exists(self, db_name):
        return db_name in self.__get_connection().list_database_names()

    def is_col_exists(self, db_name, collection_name):
        col = self.get_origin_collection(db_name, collection_name)
        return col is not None

    def get_user_collection(self, user_did, app_did, collection_name, create_on_absence=False):
        return self.get_origin_collection(self.get_user_database_name(user_did, app_did),
                                          collection_name, create_on_absence)

    def get_user_database_name(self, user_did, app_did):
        db_name = gene_mongo_db_name(user_did, app_did)
        logging.info(f'Choose the use database: {user_did}, {app_did}, {db_name}')
        return db_name

    def get_database_size(self, db_name):
        if not self.is_database_exists(db_name):
            return 0
        return self.__get_connection()[db_name].command("dbstats")["dataSize"]

    def get_origin_collection(self, db_name, collection_name, create_on_absence=False):
        db = self.__get_connection()[db_name]
        if collection_name not in db.list_collection_names():
            if not create_on_absence:
                return None
            else:
                db.create_collection(collection_name)
        return db[collection_name]

    def get_all_database_names(self):
        return self.__get_connection().list_database_names()

    def get_all_user_database_names(self, user_did=None):
        names = [name for name in self.get_all_database_names() if name.startswith(get_user_database_prefix())]
        if not user_did:
            return names
        user_apps = self.get_all_user_apps()
        result = []
        for app in user_apps:
            db_name = self.get_user_database_name(app[USER_DID], app[APP_ID])
            if db_name in names:
                result.append(db_name)
        return result

    def get_vault_service(self, user_did):
        return self.__get_connection()[DID_INFO_DB_NAME][VAULT_SERVICE_COL].find_one({VAULT_SERVICE_DID: user_did})

    def check_vault_access(self, user_did, access_vault=None):
        """
        Check if the vault can be accessed by specific permission
        """
        info = self.get_vault_service(user_did)
        if not info:
            raise VaultNotFoundException()

        # INFO: no need check permission.
        # if (access_vault == VAULT_ACCESS_WR or access_vault == VAULT_ACCESS_DEL) \
        #         and info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE:
        #     raise ForbiddenException(msg="The vault can't be written.")

    def find_many(self, user_did, app_did, collection_name, col_filter, options=None, throw_exception=True):
        col = self.get_user_collection(user_did, app_did, collection_name)
        if not col:
            if not throw_exception:
                return []
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return list(col.find(convert_oid(col_filter) if col_filter else None, **(options if options else {})))

    def find_many_origin(self, db_name, collection_name, col_filter,
                         options=None, create_on_absence=True, throw_exception=True):
        col = self.get_origin_collection(db_name, collection_name, create_on_absence=create_on_absence)
        if not col:
            if not throw_exception:
                return []
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return list(col.find(convert_oid(col_filter) if col_filter else None, **(options if options else {})))

    def find_one(self, user_did, app_did, collection_name, col_filter, options=None,
                 create_on_absence=False, throw_exception=True):
        return self.find_one_origin(self.get_user_database_name(user_did, app_did),
                                    collection_name, col_filter, options,
                                    create_on_absence=create_on_absence, throw_exception=throw_exception)

    def find_one_origin(self, db_name, collection_name, col_filter, options=None,
                        create_on_absence=False, throw_exception=True):
        col = self.get_origin_collection(db_name, collection_name, create_on_absence=create_on_absence)
        if not create_on_absence and not col:
            if not throw_exception:
                return None
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return col.find_one(convert_oid(col_filter) if col_filter else None, **(options if options else {}))

    def insert_one(self, user_did, app_did, collection_name, document, options=None, create_on_absence=False, **kwargs):
        return self.insert_one_origin(self.get_user_database_name(user_did, app_did), collection_name, document,
                                      options, create_on_absence, **kwargs)

    def insert_one_origin(self, db_name, collection_name, document, options=None,
                          create_on_absence=False, is_extra=True, **kwargs):
        col = self.get_origin_collection(db_name, collection_name, create_on_absence)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        if is_extra:
            now_timestamp = datetime.now().timestamp()
            document['created'] = now_timestamp if not kwargs.get('created') else kwargs.get('created')
            document['modified'] = now_timestamp if not kwargs.get('modified') else kwargs.get('modified')

        result = col.insert_one(convert_oid(document), **(options if options else {}))
        return {
            "acknowledged": result.acknowledged,
            "inserted_id": str(result.inserted_id) if result.inserted_id else ''
        }

    def update_one(self, user_did, app_did, collection_name, col_filter, col_update, options=None,
                   is_extra=False, **kwargs):
        return self.update_one_origin(self.get_user_database_name(user_did, app_did), collection_name,
                                      col_filter, col_update,
                                      options=options, is_extra=is_extra, **kwargs)

    def update_one_origin(self, db_name, collection_name, col_filter, col_update,
                          options=None, create_on_absence=False, is_many=False, is_extra=False, **kwargs):
        col = self.get_origin_collection(db_name, collection_name, create_on_absence=create_on_absence)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        if is_extra:
            now_timestamp = datetime.now().timestamp()
            if '$setOnInsert' in col_update:
                col_update["$setOnInsert"]['created'] = now_timestamp
            else:
                col_update["$setOnInsert"] = {"created": now_timestamp}
            if "$set" in col_update:
                col_update["$set"]["modified"] = now_timestamp if not kwargs.get('modified') else kwargs.get('modified')

        if is_many:
            result = col.update_many(convert_oid(col_filter), convert_oid(col_update, update=True), **(options if options else {}))
        else:
            result = col.update_one(convert_oid(col_filter), convert_oid(col_update, update=True), **(options if options else {}))
        return {
            "acknowledged": result.acknowledged,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else '',
        }

    def delete_one(self, user_did, app_did, collection_name, col_filter, is_check_exist=True):
        return self.delete_one_origin(self.get_user_database_name(user_did, app_did),
                                      collection_name, col_filter, is_check_exist=is_check_exist)

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
            raise BadRequestException(msg='Failed to save the file content to local.')

    def create_collection(self, user_did, app_did, collection_name):
        try:
            self.__get_connection()[self.get_user_database_name(user_did, app_did)].create_collection(collection_name)
        except CollectionInvalid as e:
            logging.error('The collection already exists.')
            raise AlreadyExistsException()

    def delete_collection(self, user_did, app_did, collection_name, is_check_exist=True):
        if is_check_exist and not self.get_user_collection(user_did, app_did, collection_name):
            raise CollectionNotFoundException()
        self.__get_connection()[self.get_user_database_name(user_did, app_did)].drop_collection(collection_name)

    def delete_collection_origin(self, db_name, collection_name):
        if self.get_origin_collection(db_name, collection_name):
            raise CollectionNotFoundException()
        self.__get_connection()[db_name].drop_collection(collection_name)

    def remove_database(self, user_did, app_did):
        self.__get_connection().drop_database(self.get_user_database_name(user_did, app_did))

    def timestamp_to_epoch(self, timestamp):
        if timestamp < 0:
            return timestamp
        t = datetime.fromtimestamp(timestamp)
        s = datetime(1970, 1, 1, 0, 0, 0)
        return int((t - s).total_seconds())

    def get_all_user_apps(self, user_did=None):
        # INFO: Need consider the adaptation of the old user information.
        query = {APP_INSTANCE_DID: {'$exists': True}, APP_ID: {'$exists': True}, USER_DID: {'$exists': True}}
        if user_did:
            query[USER_DID] = user_did
        docs = self.find_many_origin(DID_INFO_DB_NAME,
                                     DID_INFO_REGISTER_COL, query, create_on_absence=False, throw_exception=False)
        if not docs:
            return list()
        return get_unique_dict_item_from_list([{USER_DID: d[USER_DID], APP_ID: d[APP_ID]} for d in docs])

    def get_all_user_dids(self):
        user_apps = self.get_all_user_apps()
        return list(set([d[USER_DID] for d in user_apps]))


cli = DatabaseClient()


if __name__ == '__main__':
    # Compute the user's database name.
    db_name = cli.get_user_database_name('did:elastos:idXWuMoHYYhhGjigKwEidw7ZPDauPC5FU7',
                                         'did:elastos:ig1nqyyJhwTctdLyDFbZomSbZSjyMN1uor')
    print(db_name)
