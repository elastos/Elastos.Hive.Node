import jwt

from src import hive_setting
from src.utils.consts import COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_SHA256, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
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
        vault = self.vault_manager.get_vault(self.get_target_did())
        if action_type == 'upload':
            vault.check_write_permission().check_storage_full()

        # The created transaction record can only be use once. So do not consider run script twice.
        # If the user not call this transaction later, the transaction record will keep forever.
        col = self.mcli.get_user_collection(self.get_target_did(), self.get_target_app_did(), SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, create_on_absence=True)
        result = col.insert_one({
            "document": {
                "file_name": self.get_populated_path(),
                "fileapi_type": action_type
            },
            'anonymous': self.script.anonymous_app and self.script.anonymous_user
        })

        return {
            "transaction_id": jwt.encode({
                    "row_id": result['inserted_id'],
                    "target_did": self.get_target_did(),
                    "target_app_did": self.get_target_app_did()
                }, hive_setting.PASSWORD, algorithm='HS256')
        }


class FileUploadExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self.get_result_data(self._create_transaction('upload'))


class FileDownloadExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self.get_result_data(self._create_transaction('download'))


class FilePropertiesExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did())

        path = self.get_populated_path()

        doc = self.ipfs_files.get_file_metadata(self.get_target_did(), self.get_target_app_did(), path)
        return self.get_result_data({
            "type": "file" if doc[COL_IPFS_FILES_IS_FILE] else "folder",
            "name": path,
            "size": doc[SIZE],
            "last_modify": int(doc['modified'])
        })


class FileHashExecutable(FileExecutable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did())

        doc = self.ipfs_files.get_file_metadata(self.get_target_did(), self.get_target_app_did(), self.get_populated_path())
        return self.get_result_data({"SHA256": doc[COL_IPFS_FILES_SHA256]})
