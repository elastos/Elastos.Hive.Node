from src.modules.database.mongodb_client import mcli
from src.modules.database.mongodb_collection import MongodbCollection, mongodb_collection, CollectionName, CollectionGenericField


@mongodb_collection(CollectionName.COLLECTION_METADATA, is_management=False, is_internal=True)
class CollectionMetadata(MongodbCollection):
    """ Collection metadata keeps the information for user's application collections.
    The metadata collection is under user's application database.

    """

    # fields
    USR_DID = CollectionGenericField.USR_DID
    APP_DID = CollectionGenericField.APP_DID
    NAME = CollectionGenericField.NAME
    IS_ENCRYPT = 'is_encrypt'
    ENCRYPT_METHOD = 'encrypt_method'

    def __init__(self, col):
        MongodbCollection.__init__(self, col)

    def sync_all_cols(self):
        names = mcli.get_user_collection_names(self.user_did, self.app_did)
        for name in names:
            self.add_col(name, False, '')

    def add_col(self, col_name, is_encrypt, encrypt_method):
        update = {'$setOnInsert': {
            self.IS_ENCRYPT: is_encrypt,
            self.ENCRYPT_METHOD: encrypt_method}}

        self.update_one(self._get_internal_filter(col_name), update, contains_extra=True, upsert=True)

    def delete_col(self, col_name):
        self.delete_one(self._get_internal_filter(col_name))

    def get_col(self, col_name):
        return self.find_one(self._get_internal_filter(col_name))

    def get_all_cols(self):
        return self.find_many({})

    def _get_internal_filter(self, col_name):
        return {
            self.USR_DID: self.user_did,
            self.APP_DID: self.app_did,
            self.NAME: col_name,
        }
