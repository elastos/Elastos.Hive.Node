import hashlib
import logging
import typing
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from src import hive_setting
from src.utils.consts import DID_INFO_DB_NAME
from src.utils.http_exception import CollectionNotFoundException, AlreadyExistsException, BadRequestException

_T = typing.TypeVar('_T', dict, list, tuple)


class Dotdict(dict):
    """ Base class for all mongodb document.

    if you define a document like this (all keys must be underscore):

        {
            "did": "xxx",
            "max_storage": 2097152000,
            "pricing_using": "Rockie"
        }

    Then you can define class like this. So please just use in the class.

        class Vault(Dotdict):
            def get_user_did():
                return self.did

    Usage like this:

        vault = Vault(**doc)

    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class MongodbCollection:
    """ all collection wrapper and base class for specific collection

    NOTE: Do not directly create the instance from this class.

    """

    def __init__(self, col, is_management=True):
        # Collection from pymongo
        self.col = col

        # management means internal collection which do not support extra features
        self.is_management = is_management

    def insert_one(self, doc, contains_extra=True, **kwargs):
        if contains_extra:
            doc['created'] = doc['modified'] = int(datetime.now().timestamp())

        # kwargs are the options
        options = {k: v for k, v in kwargs.items() if k in ["bypass_document_validation"]}

        result = self.col.insert_one(self.convert_oid(doc), **options)
        if not result.inserted_id:
            raise BadRequestException(f'Failed to insert the doc: {str(doc)}.')

        return {
            "acknowledged": result.acknowledged,
            "inserted_id": str(result.inserted_id)  # ObjectId -> str
        }

    def insert_many(self, docs, contains_extra=True, **kwargs):
        if contains_extra:
            for doc in docs:
                doc['created'] = doc['modified'] = int(datetime.now().timestamp())

        # kwargs are the options
        options = {k: v for k, v in kwargs.items() if k in ["ordered", "bypass_document_validation"]}

        result = self.col.insert_many(self.convert_oid(docs), **options)
        if len(result.inserted_ids) < len(docs):
            raise BadRequestException(f'Failed to insert the docs: {str(docs)}.')

        return {
            "acknowledged": result.acknowledged,
            "inserted_ids": [str(oid) for oid in result.inserted_ids]  # ObjectId -> str
        }

    def update_one(self, filter_, update, contains_extra=True, **kwargs):
        return self.update_many(filter_, update, contains_extra=contains_extra, only_one=True, **kwargs)

    def update_many(self, filter_, update, contains_extra=True, only_one=False, **kwargs):
        if contains_extra:
            now_timestamp = int(datetime.now().timestamp())

            # for normal update
            if "$set" in update:
                update["$set"]["modified"] = now_timestamp
            else:
                update["$set"] = {"modified": now_timestamp}

            # for insert if not exists
            if kwargs.get('upsert', False):
                if "$setOnInsert" in update:
                    update["$setOnInsert"]["created"] = now_timestamp
                else:
                    update["$setOnInsert"] = {"created": now_timestamp}

        # kwargs are the options, and filter them
        options = {k: v for k, v in kwargs.items() if k in ("upsert", "bypass_document_validation")}

        if only_one:
            result = self.col.update_one(self.convert_oid(filter_) if filter_ else {}, self.convert_oid(update), **options)
        else:
            result = self.col.update_many(self.convert_oid(filter_) if filter_ else {}, self.convert_oid(update), **options)
        return {
            "acknowledged": result.acknowledged,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }

    def replace_one(self, filter_, document, upsert=True):
        # default 'bypass_document_validation': False
        result = self.col.replace_one(self.convert_oid(filter_) if filter_ else None, self.convert_oid(document), upsert=upsert)
        return {
            "acknowledged": result.acknowledged,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None  # ObjectId -> str
        }

    def find_one(self, filter_: dict, **kwargs) -> dict:
        """ Note: the result document contains ObjectId or other types
        which can not directly take as response body. """
        result = self.find_many(filter_, only_one=True, **kwargs)
        return result[0] if result else None

    def find_many(self, filter_: dict, only_one=False, **kwargs) -> list:
        """ Note: the result documents contain ObjectId or other types
                which can not directly take as response body. """

        # kwargs are the options
        options = {k: v for k, v in kwargs.items() if k in ("projection",
                                                            "skip",
                                                            "limit",
                                                            "sort",
                                                            "allow_partial_results",
                                                            "return_key",
                                                            "show_record_id",
                                                            "batch_size")}

        # extra sort support
        if 'sort' in options:
            if isinstance(options['sort'], dict):
                # value example: {'author', -1} => [('author', -1)]
                options['sort'] = [(k, v) for k, v in options['sort'].items()]

        # BUGBUG: Getting all documents out maybe not well.
        if only_one:
            result = self.col.find_one(self.convert_oid(filter_) if filter_ else None, **kwargs)
            return [] if result is None else [result]

        return list(self.col.find(self.convert_oid(filter_) if filter_ else None, **options))

    def count(self, filter_, **kwargs):
        options = {k: v for k, v in kwargs.items() if k in ("skip", "limit", "maxTimeMS")}

        return self.col.count_documents(self.convert_oid(filter_) if filter_ else {}, **options)

    def delete_one(self, filter_):
        return self.delete_many(filter_, only_one=True)

    def delete_many(self, filter_, only_one=False):
        if only_one:
            result = self.col.delete_one(self.convert_oid(filter_) if filter_ else None)
        else:
            result = self.col.delete_many(self.convert_oid(filter_) if filter_ else None)
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count
        }

    def distinct(self, field: str) -> list:
        return self.col.distinct(field)

    def convert_oid(self, value: _T):
        """ try to convert the following dict recursively.

            { "group_id": {"$oid": "5f497bb83bd36ab235d82e6a"} }

        to:

            { "group_id": ObjectId("5f497bb83bd36ab235d82e6a") }
        """
        # The management collection do not do $oid checking.
        if self.is_management:
            return value

        if type(value) in (list, tuple):
            for o in value:
                if isinstance(o, dict) or type(o) in (list, tuple):
                    self.convert_oid(o)
        elif isinstance(value, dict):
            for k, v in value.copy().items():
                if isinstance(v, dict):
                    if '$oid' in v:
                        value[k] = ObjectId(v['$oid'])
                    else:
                        value[k] = self.convert_oid(v)
                elif type(v) in (list, tuple):
                    value[k] = self.convert_oid(v)
        return value


class MongodbClient:
    """ Used to connect mongodb and is a helper class for all mongo database operation. """

    def __init__(self):
        self.mongodb_uri = hive_setting.MONGODB_URL
        self.connection = None

    def __get_connection(self):
        if not self.connection:
            self.connection = MongoClient(self.mongodb_uri)
        return self.connection

    def __get_database(self, name):
        """ All databases (manager or user) must exist before call this method.

        Database contains:
            1. one management database with fixed name.
            2. multiple user databases whose name is generated by user did and app did.
        """
        return self.__get_connection()[name]

    def exists_database(self, name):
        return name in self.__get_connection().list_database_names()

    def exists_user_database(self, user_did, app_did):
        return self.exists_database(MongodbClient.get_user_database_name(user_did, app_did))

    def exists_user_collection(self, user_did, app_did, col_name):
        database_name = MongodbClient.get_user_database_name(user_did, app_did)
        if not self.exists_database(database_name):
            return False

        return col_name not in self.__get_database(database_name).list_collection_names()

    @staticmethod
    def get_user_database_name(user_did, app_did):
        # The length of database name is limited to 38 on Atlas Mongodb.
        # https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/ @ key: Namespaces and Database Names
        prefix = 'hive_user_db_' if not hive_setting.ATLAS_ENABLED else 'hu_'

        # The length of md5 string is 32.
        md5 = hashlib.md5()
        md5.update((user_did + "_" + app_did).encode("utf-8"))
        return prefix + str(md5.hexdigest())

    def get_management_collection(self, col_name) -> MongodbCollection:
        """ Get internal usage collection.

        All manager collection must exist before call this method.
        """
        database = self.__get_database(DID_INFO_DB_NAME)

        # Directly create manager collection if not exists.
        if col_name not in database.list_collection_names():
            database.create_collection(col_name)
        return MongodbCollection(database[col_name])

    def get_user_collection(self, user_did: str, app_did: str, col_name, create_on_absence=False) -> MongodbCollection:
        """ User collection belongs to user database and maybe need check the existence.

        :raise: CollectionNotFoundException
        """
        database = self.__get_database(MongodbClient.get_user_database_name(user_did, app_did))
        if col_name not in database.list_collection_names():
            if create_on_absence:
                database.create_collection(col_name)
            else:
                raise CollectionNotFoundException(f'Can not find collection {col_name}')
        return MongodbCollection(database[col_name], is_management=False)

    def create_user_collection(self, user_did, app_did, col_name) -> MongodbCollection:
        database_name = MongodbClient.get_user_database_name(user_did, app_did)
        database = self.__get_database(database_name)
        try:
            return MongodbCollection(database.create_collection(col_name), is_management=False)
        except CollectionInvalid as e:
            logging.info(f'The collection {database_name}.{col_name} already exists.')
            raise AlreadyExistsException()

    def delete_user_collection(self, user_did, app_did, col_name, check_exist=False):
        database = self.__get_database(MongodbClient.get_user_database_name(user_did, app_did))
        if col_name not in database.list_collection_names():
            if check_exist:
                raise CollectionNotFoundException(f"Can not found user's collection {col_name}")
        else:
            database.drop_collection(col_name)

    def drop_user_database(self, user_did, app_did):
        name = MongodbClient.get_user_database_name(user_did, app_did)
        if self.exists_database(name):
            self.__get_connection().drop_database(name)

    def get_user_database_size(self, user_did, app_did) -> int:
        """ Get the size of the user database, if not exist, return 0 """
        name = self.get_user_database_name(user_did, app_did)
        if not self.exists_database(name):
            return 0

        database = self.__get_database(name)

        # count size by command: https://www.mongodb.com/docs/v4.4/reference/command/dbStats/
        return int(database.command('dbstats')['totalSize'])
