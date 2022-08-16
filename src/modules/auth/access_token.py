import uuid

from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import DID_INFO_REGISTER_COL, DID_INFO_NONCE, APP_INSTANCE_DID, USER_DID, APP_ID, DID_INFO_TOKEN, DID_INFO_TOKEN_EXPIRED


class AccessToken:
    def __init__(self):
        self.mcli = MongodbClient()

    @staticmethod
    def create_nonce():
        return str(uuid.uuid1())

    def get_auth_info_by_nonce(self, nonce):
        filter_ = {DID_INFO_NONCE: nonce}
        return self.mcli.get_management_collection(DID_INFO_REGISTER_COL).find_one(filter_)

    def update_auth_info(self, did, app_did, app_instance_did, nonce, token, expired):
        filter_ = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce}
        update = {"$set": {
            USER_DID: did,
            APP_ID: app_did,
            DID_INFO_TOKEN: token,
            DID_INFO_TOKEN_EXPIRED: expired
        }}
        return self.mcli.get_management_collection(DID_INFO_REGISTER_COL).update_one(filter_, update, contains_extra=False)
