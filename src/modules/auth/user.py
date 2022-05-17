from src.modules.database.mongodb_client import MongodbClient
from src.utils_v1.constants import APP_ID, USER_DID, DID_INFO_REGISTER_COL


class UserManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def get_all_app_dids(self, user_did):
        """ Get all applications DIDs belonged to user DID """
        col = self.mcli.get_management_collection(DID_INFO_REGISTER_COL)
        # INFO: Must check the existence of some fields
        filter_ = {
            APP_ID: {'$exists': True},
            '$and': [{USER_DID: {'$exists': True}}, {USER_DID: user_did}]
        }
        docs = col.find_many(filter_)
        return list(set(map(lambda d: d[APP_ID], docs)))
