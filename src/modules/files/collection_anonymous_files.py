from src.modules.database.mongodb_collection import MongodbCollection, mongodb_collection
from src.utils.consts import COL_ANONYMOUS_FILES_USR_DID, COL_ANONYMOUS_FILES_APP_DID, COL_ANONYMOUS_FILES_NAME, COL_ANONYMOUS_FILES_CID, COL_ANONYMOUS_FILES


@mongodb_collection(COL_ANONYMOUS_FILES, is_management=False, is_internal=True)
class CollectionAnonymousFiles(MongodbCollection):
    """ Anonymous file is a public file which can be access by scripting module anonymously. """

    def __init__(self, col):
        MongodbCollection.__init__(self, col)

    def add_anonymous_file(self, name, cid):
        from src.modules.scripting.scripting import Scripting
        Scripting().set_anonymous_file_script()

        filter_ = {
            COL_ANONYMOUS_FILES_USR_DID: self.user_did,
            COL_ANONYMOUS_FILES_APP_DID: self.app_did,
            COL_ANONYMOUS_FILES_NAME: name}
        update = {'$setOnInsert': {
            COL_ANONYMOUS_FILES_CID: cid}}
        self.update_one(filter_, update, contains_extra=True, upsert=True)

    def delete_anonymous_file(self, name):
        filter_ = {
            COL_ANONYMOUS_FILES_USR_DID: self.user_did,
            COL_ANONYMOUS_FILES_APP_DID: self.app_did,
            COL_ANONYMOUS_FILES_NAME: name}
        self.delete_one(filter_)
