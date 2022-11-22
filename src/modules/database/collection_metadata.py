from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_COLLECTION_METADATA_USR_DID, COL_COLLECTION_METADATA_APP_DID, COL_COLLECTION_METADATA_NAME, COL_COLLECTION_METADATA_IS_ENCRYPT, \
    COL_COLLECTION_METADATA_ENCRYPT_METHOD, COL_COLLECTION_METADATA


class CollectionMetadata:
    """ Collection metadata keeps the information for user's application collections.
    The metadata collection is under user's application database.

    """

    def __init__(self):
        self.mcli = MongodbClient()

    def sync_all(self, user_did, app_did):
        names = self.mcli.get_user_collection_names(user_did, app_did)
        for name in names:
            self.add(user_did, app_did, name, False, '')

    def add(self, user_did, app_did, collection_name, is_encrypt, encrypt_method):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: user_did,
            COL_COLLECTION_METADATA_APP_DID: app_did,
            COL_COLLECTION_METADATA_NAME: collection_name,
        }

        update = {'$setOnInsert': {
            COL_COLLECTION_METADATA_IS_ENCRYPT: is_encrypt,
            COL_COLLECTION_METADATA_ENCRYPT_METHOD: encrypt_method}}

        self.mcli.get_user_collection(user_did, app_did, COL_COLLECTION_METADATA,
                                      create_on_absence=True).update_one(filter_, update, contains_extra=True, upsert=True)

    def delete(self, user_did, app_did, collection_name):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: user_did,
            COL_COLLECTION_METADATA_APP_DID: app_did,
            COL_COLLECTION_METADATA_NAME: collection_name,
        }
        self.mcli.get_user_collection(user_did, app_did, COL_COLLECTION_METADATA, create_on_absence=True).delete_one(filter_)

    def get(self, user_did, app_did, collection_name):
        filter_ = {
            COL_COLLECTION_METADATA_USR_DID: user_did,
            COL_COLLECTION_METADATA_APP_DID: app_did,
            COL_COLLECTION_METADATA_NAME: collection_name,
        }
        return self.mcli.get_user_collection(user_did, app_did, COL_COLLECTION_METADATA, create_on_absence=True).find_one(filter_)

    def get_all(self, user_did, app_did):
        return self.mcli.get_user_collection(user_did, app_did, COL_COLLECTION_METADATA, create_on_absence=True).find_many({})
