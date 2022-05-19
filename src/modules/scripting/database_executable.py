import json

from bson import json_util

from src.utils_v1.did_mongo_db_resource import get_mongo_database_size
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_mongodb_data
from src.modules.database.mongodb_client import MongodbClient
from src.modules.scripting.executable import Executable, get_populated_value_with_params
from src.modules.scripting.scripting import Script


class DatabaseExecutable(Executable):
    def __init__(self, script: Script, executable_data):
        super().__init__(script, executable_data)
        self.mcli = MongodbClient()

    def get_collection_name(self):
        return self.body['collection']

    def get_target_user_collection(self):
        return self.mcli.get_user_collection(self.get_target_did(), self.get_target_app_did(), self.get_collection_name())

    def get_populated_filter(self):
        return get_populated_value_with_params(self.body.get('filter', {}), self.get_user_did(), self.get_app_did(), self.get_params())

    def get_options(self):
        return self.body.get('options', {})

    def get_populated_options(self):
        return get_populated_value_with_params(self.get_options(), self.get_user_did(), self.get_app_did(), self.get_params())

    def get_populated_document(self):
        return get_populated_value_with_params(self.body.get('document', {}), self.get_user_did(), self.get_app_did(), self.get_params())

    def get_populated_update(self):
        return get_populated_value_with_params(self.body.get('update', {}), self.get_user_did(), self.get_app_did(), self.get_params())


class FindExecutable(DatabaseExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did())

        filter_, options = self.get_populated_filter(), self.get_populated_options()
        col = self.get_target_user_collection()
        items = col.find_many(filter_, **options)
        total = col.count(filter_)

        # json decode&encode is used for ObjectId or other mongo data types.
        return self.get_result_data({'total': total, 'items': json.loads(json_util.dumps(items))})


class InsertExecutable(DatabaseExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did()).check_storage()

        options = self.get_options()

        # timestamp = True, to add extra 'created' and 'modified' fields.
        is_timestamp = options.pop('timestamp', False)

        col = self.get_target_user_collection()
        result = col.insert_one(self.get_populated_filter(), self.get_populated_update(), contains_extra=is_timestamp, **options)

        update_used_storage_for_mongodb_data(self.get_user_did(), get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))
        return self.get_result_data(result)


class UpdateExecutable(DatabaseExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did()).check_storage()

        options = self.get_options()

        # timestamp = True, to update extra 'modified' fields.
        is_timestamp = options.pop('timestamp', False)

        col = self.get_target_user_collection()
        result = col.update_one(self.get_populated_filter(), self.get_populated_update(), contains_extra=is_timestamp, **options)

        update_used_storage_for_mongodb_data(self.get_user_did(), get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))
        return self.get_result_data(result)


class DeleteExecutable(DatabaseExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did())

        col = self.get_target_user_collection()
        result = col.delete_one(self.get_populated_filter())

        update_used_storage_for_mongodb_data(self.get_user_did(), get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))
        return self.get_result_data(result)
