import uuid

from src.modules.database.mongodb_collection import mongodb_collection, CollectionName, MongodbCollection


@mongodb_collection(CollectionName.REGISTER, is_management=True, is_internal=True)
class CollectionRegister(MongodbCollection):
    """ represents the application on the vault. """

    # No extra fields
    USR_DID = "userDid"  # added when /auth
    APP_ID = "appDid"  # added when /auth
    APP_INSTANCE_DID = "appInstanceDid"  # added when /signin
    NONCE = "nonce"
    TOKEN = "token"
    NONCE_EXPIRED = "nonce_expired"
    TOKEN_EXPIRED = "token_expired"

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=True)

    @staticmethod
    def generate_nonce():
        return str(uuid.uuid1())

    def get_register_app_dids(self, user_did):
        """ Get all applications DIDs belonged to user DID in the 'auth_register' collection

        @deprecated Only for syncing app_dids from CollectionRegister to CollectionApplication
        """

        # INFO: Must check the existence of some fields, or the value of some fields not exist.
        filter_ = {
            self.APP_ID: {'$exists': True},
            '$and': [{self.USR_DID: {'$exists': True}}, {self.USR_DID: user_did}]
        }
        registers = self.find_many(filter_)
        return list(set(map(lambda d: d[self.APP_ID], registers)))

    def get_register(self, nonce: str):
        return self.find_one({self.NONCE: nonce})

    def update_register_token(self, user_did, app_did, app_instance_did, nonce, token, token_expired):
        filter_ = {self.APP_INSTANCE_DID: app_instance_did, self.NONCE: nonce}
        update = {"$set": {
            self.USR_DID: user_did,
            self.APP_ID: app_did,
            self.TOKEN: token,
            self.TOKEN_EXPIRED: token_expired
        }}
        return self.update_one(filter_, update, contains_extra=False)

    def update_register_nonce(self, app_instance_did, nonce, expired):
        filter_ = {self.APP_INSTANCE_DID: app_instance_did}
        update = {
            '$set': {  # for update and insert
                self.NONCE: nonce,
                self.NONCE_EXPIRED: expired
            }
        }
        self.update_one(filter_, update, contains_extra=False, upsert=True)
