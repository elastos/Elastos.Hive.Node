from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_ANONYMOUS_FILES_USR_DID, COL_ANONYMOUS_FILES_APP_DID, COL_ANONYMOUS_FILES_NAME, COL_ANONYMOUS_FILES_CID, COL_ANONYMOUS_FILES


class AnonymousFiles:
    def __init__(self):
        self.mcli = MongodbClient()

    def add(self, user_did, app_did, name, cid):
        from src.modules.scripting.scripting import Scripting
        Scripting().set_anonymous_file_script()

        filter_ = {
            COL_ANONYMOUS_FILES_USR_DID: user_did,
            COL_ANONYMOUS_FILES_APP_DID: app_did,
            COL_ANONYMOUS_FILES_NAME: name}
        update = {'$setOnInsert': {
            COL_ANONYMOUS_FILES_CID: cid}}
        self.mcli.get_user_collection(user_did, app_did, COL_ANONYMOUS_FILES)\
            .update_one(filter_, update, contains_extra=True, upsert=True)

    def delete(self, user_did, app_did, name):
        filter_ = {
            COL_ANONYMOUS_FILES_USR_DID: user_did,
            COL_ANONYMOUS_FILES_APP_DID: app_did,
            COL_ANONYMOUS_FILES_NAME: name}
        self.mcli.get_user_collection(user_did, app_did, COL_ANONYMOUS_FILES).delete_one(filter_)
