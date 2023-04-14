from src.modules.database.mongodb_client import mcli
from src.modules.database.mongodb_collection import CollectionGenericField
from src.modules.files.collection_file_metadata import CollectionFileMetadata
from src.modules.scripting.collection_scripts_transaction import ActionType, CollectionScriptsTransaction
from src.modules.scripting.executable import Executable
from src.modules.scripting.scripting import Script


class FileExecutable(Executable):
    def __init__(self, script: Script, executable_data):
        super().__init__(script, executable_data)

    def get_populated_path(self) -> str:
        value = self.body.get('path')
        for k, v in self.get_params().items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            value = value.replace(f'$params.{k}', v)
            value = value.replace(f'${{params.{k}}}', v)
        return value

    def _create_transaction(self, action_type):
        """ Here just create a transaction for later uploading and downloading. """
        vault = mcli.get_col_vault().get_vault(self.get_target_did())
        if action_type == ActionType.UPLOAD:
            vault.check_write_permission().check_storage_full()

        # The created transaction record can only be use once. So do not consider run script twice.
        # If the user not call this transaction later, the transaction record will keep forever.
        return {
            "transaction_id":
                mcli.get_col(CollectionScriptsTransaction, user_did=self.get_target_did(), app_did=self.get_target_app_did()).
                create_script_transaction_id(self.get_populated_path(), action_type, self.script.anonymous_app and self.script.anonymous_user)
        }


class FileUploadExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self.get_result_data(self._create_transaction(ActionType.UPLOAD))


class FileDownloadExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self.get_result_data(self._create_transaction(ActionType.DOWNLOAD))


class FilePropertiesExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        mcli.get_col_vault().get_vault(self.get_target_did())

        path = self.get_populated_path()

        doc = self.files_service.v1_get_file_metadata(self.get_target_did(), self.get_target_app_did(), path)
        return self.get_result_data({
            "type": "file" if doc[CollectionFileMetadata.IS_FILE] else "folder",
            "name": path,
            "size": doc[CollectionFileMetadata.SIZE],
            "last_modify": int(doc[CollectionGenericField.MODIFIED])
        })


class FileHashExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        mcli.get_col_vault().get_vault(self.get_target_did())

        doc = self.files_service.v1_get_file_metadata(self.get_target_did(), self.get_target_app_did(), self.get_populated_path())
        return self.get_result_data({"SHA256": doc[CollectionFileMetadata.SHA256]})
