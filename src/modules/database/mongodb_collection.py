import typing
from datetime import datetime

from bson import ObjectId

from src.utils.http_exception import BadRequestException


_T = typing.TypeVar('_T', dict, list, tuple)


class CollectionName:
    # management collections
    IPFS_CID_REF = 'ipfs_cid_ref'
    APPLICATION = 'application'
    REGISTER = 'auth_register'
    VAULT_SERVICE = 'vault_service'
    BACKUP_CLIENT = 'ipfs_backup_client'
    BACKUP_SERVER = 'ipfs_backup_server'
    PAYMENT_ORDER = 'vault_order'
    PAYMENT_RECEIPT = 'vault_receipt'

    # user collections
    COLLECTION_METADATA = '__collection_metadata__'
    ANONYMOUS_FILE = '__anonymous_files__'
    FILE_METADATA = 'ipfs_files'
    SCRIPTS = 'scripts'
    SCRIPTS_TRANSACTION = 'scripts_temptx'

    @classmethod
    def is_user_internal_collection(cls, name):
        """ The collections used by node to manage cannot be operated by user. """
        return name in [
            cls.COLLECTION_METADATA,
            cls.ANONYMOUS_FILE,
            cls.FILE_METADATA,
            cls.SCRIPTS,
            cls.SCRIPTS_TRANSACTION,
        ]


class CollectionGenericField:
    CREATED = 'created'
    MODIFIED = 'modified'

    USR_DID = 'user_did'
    APP_DID = 'app_did'
    NAME = 'name'
    CID = 'cid'
    COUNT = 'count'
    SIZE = 'size'
    STATE = 'state'


def mongodb_collection(col_name, is_management=False, is_internal=True):
    """ decorator for any collection class.
    class instance user_did and app_did will be setup by mcli.get_col()
    , specific collection can choose use them.

    :param col_name: collection name.
    :param is_management: if the collection is global collection.
    :param is_internal: if the collection is internal user collection. all management collection is internal.
    """
    def wrapper(cls: type(_T)):
        cls.get_name = lambda: col_name
        cls.is_management = lambda: is_management
        cls.is_internal = lambda: is_internal
        return cls
    return wrapper


@mongodb_collection(None, is_management=True, is_internal=True)
class MongodbCollection:
    """ all collection wrapper and base class for specific collection

    NOTE: Do not directly create the instance from this class.
    This class creation is only under MongodbClient.

    """

    def __init__(self, col, is_management=True):
        """
        :param is_management: the collection is global one (not under user app database)
        TODO: remove is_management
        """
        # Collection from pymongo
        self.col = col

        # management means internal collection which do not support extra features
        self.is_management = is_management

    def insert_one(self, doc, contains_extra=True, **kwargs):
        if contains_extra:
            doc[CollectionGenericField.CREATED] = doc[CollectionGenericField.MODIFIED] = int(datetime.now().timestamp())

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
                doc[CollectionGenericField.CREATED] = doc[CollectionGenericField.MODIFIED] = int(datetime.now().timestamp())

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
                update["$set"][CollectionGenericField.MODIFIED] = now_timestamp
            else:
                update["$set"] = {CollectionGenericField.MODIFIED: now_timestamp}

            # for insert if not exists
            if kwargs.get('upsert', False):
                if "$setOnInsert" in update:
                    update["$setOnInsert"][CollectionGenericField.CREATED] = now_timestamp
                else:
                    update["$setOnInsert"] = {CollectionGenericField.CREATED: now_timestamp}

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
        """ if upsert is True and old one not exists, create a new one. """
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
