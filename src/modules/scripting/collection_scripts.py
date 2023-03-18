from src.modules.files.collection_anonymous_files import CollectionAnonymousFiles
from src.utils.consts import SCRIPTING_SCRIPT_COLLECTION
from src.modules.database.mongodb_collection import mongodb_collection, MongodbCollection


@mongodb_collection(SCRIPTING_SCRIPT_COLLECTION, is_management=False, is_internal=True)
class CollectionScripts(MongodbCollection):
    """ This class keeps scripts for data and file sharing. """

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=False)

    def find_scripts(self, script_name=None, skip=None, limit=None):
        if script_name:
            filter_ = {'name': script_name}
        else:
            filter_ = {'name': {'$ne': CollectionAnonymousFiles.SCRIPT_NAME}}

        options = {}
        if skip:
            options['skip'] = skip
        if limit:
            options['limit'] = limit

        return self.find_many(filter_, **options)

    def find_script(self, script_name):
        return self.find_one({'name': script_name})

    def upsert_script(self, script_name, content):
        return self.update_one({'name': script_name}, {'$setOnInsert': content}, contains_extra=True, upsert=True)

    def replace_script(self, script_name, content):
        """ replace old one or create new one. """
        return self.replace_one({"name": script_name}, content)

    def delete_script(self, script_name):
        return self.delete_one({'name': script_name})
