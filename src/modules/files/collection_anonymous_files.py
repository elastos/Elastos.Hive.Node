from src.modules.database.mongodb_collection import MongodbCollection, mongodb_collection, CollectionGenericField, CollectionName


@mongodb_collection(CollectionName.ANONYMOUS_FILE, is_management=False, is_internal=True)
class CollectionAnonymousFiles(MongodbCollection):
    """ Anonymous file is a public file which can be access by scripting module anonymously.

    TODO: rename to CollectionAnonymousFile
    """

    # fields
    USR_DID = CollectionGenericField.USR_DID
    APP_DID = CollectionGenericField.APP_DID
    NAME = CollectionGenericField.NAME
    CID = CollectionGenericField.CID

    SCRIPT_NAME = '__anonymous_files__'

    def __init__(self, col):
        MongodbCollection.__init__(self, col)

    def save_anonymous_file(self, path, cid):
        from src.modules.scripting.scripting import Scripting
        Scripting().set_anonymous_file_script()

        update = {'$setOnInsert': {
            self.CID: cid}}
        self.update_one(self._get_filter(path), update, contains_extra=True, upsert=True)

    def delete_anonymous_file(self, path):
        self.delete_one(self._get_filter(path))

    def _get_filter(self, path):
        return {
            self.USR_DID: self.user_did,
            self.APP_DID: self.app_did,
            self.NAME: path
        }
