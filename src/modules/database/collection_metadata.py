from src.modules.database.mongodb_client import mcli
from src.modules.database.mongodb_collection import MongodbCollection, mongodb_collection
from src.utils.consts import COL_COLLECTION_METADATA_USR_DID, COL_COLLECTION_METADATA_APP_DID, COL_COLLECTION_METADATA_NAME, \
    COL_COLLECTION_METADATA_IS_ENCRYPT, COL_COLLECTION_METADATA_ENCRYPT_METHOD, COL_COLLECTION_METADATA


@mongodb_collection(COL_COLLECTION_METADATA, is_management=False, is_internal=True)
class CollectionMetadata(MongodbCollection):
    """ Collection metadata keeps the information for user's application collections.
    The metadata collection is under user's application database.

    """
    def __init__(self, col):
        MongodbCollection.__init__(self, col)

    def sync_all_cols(self):
        names = mcli.get_user_collection_names(self.user_did, self.app_did)
        for name in names:
            self.add_col(name, False, '')

    def add_col(self, col_name, is_encrypt, encrypt_method):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: self.user_did,
            COL_COLLECTION_METADATA_APP_DID: self.app_did,
            COL_COLLECTION_METADATA_NAME: col_name,
        }

        update = {'$setOnInsert': {
            COL_COLLECTION_METADATA_IS_ENCRYPT: is_encrypt,
            COL_COLLECTION_METADATA_ENCRYPT_METHOD: encrypt_method}}

        self.update_one(filter_, update, contains_extra=True, upsert=True)

    def delete_col(self, col_name):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: self.user_did,
            COL_COLLECTION_METADATA_APP_DID: self.app_did,
            COL_COLLECTION_METADATA_NAME: col_name,
        }
        self.delete_one(filter_)

    def get_col(self, col_name):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: self.user_did,
            COL_COLLECTION_METADATA_APP_DID: self.app_did,
            COL_COLLECTION_METADATA_NAME: col_name,
        }
        return self.find_one(filter_)

    def get_all_cols(self):
        return self.find_many({})
