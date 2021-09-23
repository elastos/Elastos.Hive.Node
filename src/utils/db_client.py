# -*- coding: utf-8 -*-

"""
Any database operations can be found here.
"""
import logging
import subprocess
from pathlib import Path

from pymongo.errors import CollectionInvalid

from src.settings import hive_setting
from src.utils.consts import BACKUP_FILE_SUFFIX, get_unique_dict_item_from_list

from src.utils_v1.did_info import get_all_did_info_by_did
from src.utils_v1.did_mongo_db_resource import gene_mongo_db_name, convert_oid, \
    export_mongo_db, get_save_mongo_db_path, create_db_client, get_user_database_prefix
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, DATETIME_FORMAT, \
    USER_DID, APP_ID, DID_INFO_REGISTER_COL, APP_INSTANCE_DID
from src.utils.http_exception import BadRequestException, AlreadyExistsException, \
    VaultNotFoundException, CollectionNotFoundException
from datetime import datetime

import os

from src.utils_v1.payment.vault_backup_service_manage import get_vault_backup_path

VAULT_SERVICE_FREE = "Free"
VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_FREEZE = "freeze"


class DatabaseClient:
    def __init__(self):
        self.is_mongo_atlas = hive_setting.is_mongodb_atlas()
        self.host = hive_setting.MONGO_HOST
        self.port = hive_setting.MONGO_PORT
        self.connection = None

    def __get_connection(self):
        if not self.connection:
            self.connection = create_db_client()
        return self.connection

    def start_session(self):
        return self.__get_connection().start_session()

    def is_database_exists(self, db_name):
        return db_name in self.__get_connection().list_database_names()

    def is_col_exists(self, db_name, collection_name):
        col = self.get_origin_collection(db_name, collection_name)
        return col is not None

    def get_user_collection(self, did, app_id, collection_name, is_create=False):
        return self.get_origin_collection(gene_mongo_db_name(did, app_id), collection_name, is_create)

    def get_origin_collection(self, db_name, collection_name, is_create=False):
        db = self.__get_connection()[db_name]
        if collection_name not in db.list_collection_names():
            if not is_create:
                return None
            else:
                db.create_collection(collection_name)
        return db[collection_name]

    def get_all_database_names(self):
        return self.__get_connection().list_database_names()

    def get_all_user_database_names(self, did=None):
        names = [name for name in self.get_all_database_names() if name.startswith(get_user_database_prefix())]
        if not did:
            return names
        user_apps = self.get_all_user_apps()
        result = []
        for app in user_apps:
            db_name = gene_mongo_db_name(app[USER_DID], app[APP_ID])
            if db_name in names:
                result.append(db_name)
        return result

    def get_vault_service(self, did):
        return self.__get_connection()[DID_INFO_DB_NAME][VAULT_SERVICE_COL].find_one({VAULT_SERVICE_DID: did})

    def check_vault_access(self, did, access_vault=None):
        """
        Check if the vault can be accessed by specific permission
        """
        info = self.get_vault_service(did)
        if not info:
            raise VaultNotFoundException()

        # INFO: no need check permission.
        # if (access_vault == VAULT_ACCESS_WR or access_vault == VAULT_ACCESS_DEL) \
        #         and info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE:
        #     raise ForbiddenException(msg="The vault can't be written.")

    def find_many(self, did, app_id, collection_name, col_filter, options=None):
        col = self.get_user_collection(did, app_id, collection_name)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return list(col.find(convert_oid(col_filter) if col_filter else None, **(options if options else {})))

    def find_many_origin(self, db_name, collection_name, col_filter, options=None, is_create=True, is_raise=True):
        col = self.get_origin_collection(db_name, collection_name, is_create=is_create)
        if not col:
            if not is_raise:
                return []
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return list(col.find(convert_oid(col_filter) if col_filter else None, **(options if options else {})))

    def find_one(self, did, app_id, collection_name, col_filter, options=None, is_create=False, is_raise=True):
        return self.find_one_origin(gene_mongo_db_name(did, app_id),
                                    collection_name, col_filter, options, is_create=is_create, is_raise=is_raise)

    def find_one_origin(self, db_name, collection_name, col_filter, options=None, is_create=False, is_raise=True):
        col = self.get_origin_collection(db_name, collection_name, is_create=is_create)
        if not is_create and not col:
            if not is_raise:
                return None
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)
        return col.find_one(convert_oid(col_filter) if col_filter else None, **(options if options else {}))

    def insert_one(self, did, app_id, collection_name, document, options=None, is_create=False):
        return self.insert_one_origin(gene_mongo_db_name(did, app_id), collection_name, document, options, is_create)

    def insert_one_origin(self, db_name, collection_name, document, options=None, is_create=False, is_extra=True):
        col = self.get_origin_collection(db_name, collection_name, is_create)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        if is_extra:
            document['created'] = datetime.strptime(document["created"], DATETIME_FORMAT) \
                if 'created' in document else datetime.utcnow()
            document['modified'] = datetime.utcnow()

        result = col.insert_one(convert_oid(document), **(options if options else {}))
        return {
            "acknowledged": result.acknowledged,
            "inserted_id": str(result.inserted_id) if result.inserted_id else ''
        }

    def update_one(self, did, app_id, collection_name, col_filter, col_update, options=None, is_extra=False):
        return self.update_one_origin(gene_mongo_db_name(did, app_id), collection_name,
                                      col_filter, col_update, options=options, is_extra=is_extra)

    def update_one_origin(self, db_name, collection_name, col_filter, col_update,
                          options=None, is_create=False, is_many=False, is_extra=False):
        col = self.get_origin_collection(db_name, collection_name, is_create=is_create)
        if not col:
            raise CollectionNotFoundException(msg='Cannot find collection with name ' + collection_name)

        if is_extra:
            if '$setOnInsert' in col_update:
                col_update["$setOnInsert"]['created'] = datetime.utcnow()
            else:
                col_update["$setOnInsert"] = {"created": datetime.utcnow()}
            if "$set" in col_update:
                col_update["$set"]["modified"] = datetime.utcnow()

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

    def delete_one(self, did, app_id, collection_name, col_filter, is_check_exist=True):
        return self.delete_one_origin(gene_mongo_db_name(did, app_id),
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

    def remove_database(self, did, app_did):
        self.__get_connection().drop_database(gene_mongo_db_name(did, app_did))

    def timestamp_to_epoch(self, timestamp):
        if timestamp < 0:
            return timestamp
        t = datetime.fromtimestamp(timestamp)
        s = datetime(1970, 1, 1, 0, 0, 0)
        return int((t - s).total_seconds())

    def get_all_user_apps(self, did=None):
        # INFO: Need consider the adaptation of the old user information.
        query = {APP_INSTANCE_DID: {'$exists': True}, APP_ID: {'$exists': True}, USER_DID: {'$exists': True}}
        if did:
            query[USER_DID] = did
        docs = self.find_many_origin(DID_INFO_DB_NAME,
                                     DID_INFO_REGISTER_COL, query, is_create=False, is_raise=False)
        if not docs:
            return list()
        return get_unique_dict_item_from_list([{USER_DID: d[USER_DID], APP_ID: d[APP_ID]} for d in docs])

    def get_all_user_dids(self):
        user_apps = self.get_all_user_apps()
        return list(set([d[USER_DID] for d in user_apps]))

    def export_mongodb(self, did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[USER_DID], did_info[APP_ID])

    def import_mongodb(self, did):
        """ same as import_mongo_db """
        mongodb_root = get_save_mongo_db_path(did)
        self.restore_database(mongodb_root)

    def import_mongodb_in_backup_server(self, did):
        vault_dir = get_vault_backup_path(did)
        self.restore_database(vault_dir)

    def restore_database(self, root_dir: Path):
        if not root_dir.exists():
            logging.info('The backup root dir does not exist, skip restore.')
            return

        # restore the data of the database from every 'dump_file'.
        dump_files = [x for x in root_dir.iterdir() if x.suffix == BACKUP_FILE_SUFFIX]
        for dump_file in dump_files:
            if self.is_mongo_atlas:
                line2 = f"mongorestore --uri={self.host}" \
                        f" --drop --archive='{dump_file.as_posix()}'"
            else:
                line2 = f"mongorestore -h {self.host} --port {self.port}" \
                        f" --drop --archive='{dump_file.as_posix()}'"
            logging.info(f'[db_client] restore database from file {line2}.')
            return_code = subprocess.call(line2, shell=True)
            if return_code != 0:
                raise BadRequestException(msg=f'Failed to restore mongodb data from file {dump_file.as_posix()}.')


cli = DatabaseClient()


if __name__ == '__main__':
    pass
