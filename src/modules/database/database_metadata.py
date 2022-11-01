from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_DATABASE_METADATA_USR_DID, COL_DATABASE_METADATA_APP_DID, COL_DATABASE_METADATA_NAME, COL_DATABASE_METADATA_IS_ENCRYPT, \
    COL_DATABASE_METADATA_ENCRYPT_METHOD, COL_DATABASE_METADATA


class DatabaseMetadataManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def add(self, user_did, app_did, collection_name, is_encrypt, encrypt_method):
        filter_ = {
            COL_DATABASE_METADATA_USR_DID: user_did,
            COL_DATABASE_METADATA_APP_DID: app_did,
            COL_DATABASE_METADATA_NAME: collection_name,
        }

        update = {'$setOnInsert': {
            COL_DATABASE_METADATA_IS_ENCRYPT: is_encrypt,
            COL_DATABASE_METADATA_ENCRYPT_METHOD: encrypt_method}}

        self.mcli.get_user_collection(user_did, app_did, COL_DATABASE_METADATA,
                                      create_on_absence=True).update_one(filter_, update, contains_extra=True, upsert=True)

    def delete(self, user_did, app_did, collection_name):
        filter_ = {
            COL_DATABASE_METADATA_USR_DID: user_did,
            COL_DATABASE_METADATA_APP_DID: app_did,
            COL_DATABASE_METADATA_NAME: collection_name,
        }
        self.mcli.get_user_collection(user_did, app_did, COL_DATABASE_METADATA, create_on_absence=True).delete_one(filter_)

    def get(self, user_did, app_did, collection_name):
        filter_ = {
            COL_DATABASE_METADATA_USR_DID: user_did,
            COL_DATABASE_METADATA_APP_DID: app_did,
            COL_DATABASE_METADATA_NAME: collection_name,
        }
        return self.mcli.get_user_collection(user_did, app_did, COL_DATABASE_METADATA, create_on_absence=True).find_one(filter_)
