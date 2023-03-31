from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import APP_ID, USER_DID, DID_INFO_REGISTER_COL


class UserManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def get_temp_app_dids(self, user_did):
        """ Get all applications DIDs belonged to user DID in the 'auth_register' collection

        @deprecated Only for syncing app_dids from DID_INFO_REGISTER_COL to CollectionApplication
        """
        # INFO: Must check the existence of some fields
        filter_ = {
            APP_ID: {'$exists': True},
            '$and': [{USER_DID: {'$exists': True}}, {USER_DID: user_did}]
        }
        docs = self.mcli.get_management_collection(DID_INFO_REGISTER_COL).find_many(filter_)
        return list(set(map(lambda d: d[APP_ID], docs)))
