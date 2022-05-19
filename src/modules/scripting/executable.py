from src.modules.ipfs.ipfs_files import IpfsFiles
from src.modules.scripting.database_executable import FindExecutable, InsertExecutable, UpdateExecutable, DeleteExecutable
from src.modules.scripting.file_executable import FileUploadExecutable, FileDownloadExecutable, FilePropertiesExecutable, FileHashExecutable
from src.modules.scripting.scripting import validate_exists
from src.modules.subscription.vault import VaultManager
from src.utils.http_exception import BadRequestException
from src.utils_v1.constants import SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_EXECUTABLE_TYPE_INSERT, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_CALLER_DID, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID, SCRIPTING_EXECUTABLE_PARAMS


def get_populated_value_with_params(data, user_did, app_did, params):
    """ Do some 'value' replacement on options (dict), 'key' will not change.
    "options" will be updated.

        - "$params.<parameter name>" (str) -> value (any type)
        - "$caller_did" -> did
        - "$caller_app_did" -> app_did

    :return error message, None means no error.

    """
    if not data or not params:
        return data

    def populate_value(val):
        if isinstance(val, dict):
            return get_populated_value_with_params(user_did, app_did, val, params)
        elif isinstance(val, list):  # tuple can not change the element, so skip
            return get_populated_value_with_params(user_did, app_did, val, params)
        elif isinstance(val, str):
            if val == SCRIPTING_EXECUTABLE_CALLER_DID:
                return user_did
            elif val == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                return app_did
            elif val.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                p = val.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if p not in params:
                    raise BadRequestException(f'Can not find parameter "{p}" for the script.')
                return params[p]
            return val
        else:
            return val

    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = populate_value(value)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = populate_value(data[i])
    return data


class Executable:
    """ Executable represents an action which contains operation for database and files. """

    def __init__(self, script, executable_data):
        self.script = script
        self.name = executable_data['name']
        self.body = executable_data['body']
        self.is_output = executable_data.get('output', True)
        self.ipfs_files = IpfsFiles()
        self.vault_manager = VaultManager()

    @staticmethod
    def validate_data(json_data):
        validate_exists(json_data, 'executable', ['name', 'type', 'body'])

        if json_data['type'] not in [SCRIPTING_EXECUTABLE_TYPE_AGGREGATED,
                                     SCRIPTING_EXECUTABLE_TYPE_FIND,
                                     SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                     SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                     SCRIPTING_EXECUTABLE_TYPE_DELETE,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            raise BadRequestException(msg=f"Invalid type {json_data['type']} of the executable.")

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED \
                and (not isinstance(json_data['body'], list) or len(json_data['body']) < 1):
            raise BadRequestException(msg=f"Executable body MUST be list for type "
                                          f"'{SCRIPTING_EXECUTABLE_TYPE_AGGREGATED}'.")

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FIND,
                                 SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                 SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                 SCRIPTING_EXECUTABLE_TYPE_DELETE]:
            validate_exists(json_data['body'], 'executable.body', ['collection', ])

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            validate_exists(json_data['body'], 'executable.body', ['document', ])

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            validate_exists(json_data['body'], 'executable.body', ['update', ])

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            validate_exists(json_data['body'], 'executable.body', ['path', ])
            path = json_data['body']['executable']['body']['path']
            if not path or not isinstance(path, str):
                raise BadRequestException(msg=f'Invalid parameter "path" {json_data}')

    def execute(self):
        # override
        pass

    def get_user_did(self):
        return self.script.user_did

    def get_app_did(self):
        return self.script.app_did

    def get_target_did(self):
        return self.script.context.target_did

    def get_target_app_did(self):
        return self.script.context.target_app_did

    def get_context(self):
        return self.script.context

    def get_params(self):
        return self.script.params

    def get_result_data(self, data):
        """ for response """
        return data if self.is_output else None

    @staticmethod
    def create_executables(script, executable_data) -> ['Executable']:
        result = []
        Executable.__create(result, script, executable_data)
        return result

    @staticmethod
    def __create(result, script, executable_data):
        executable_type = executable_data['type']
        executable_body = executable_data['body']
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for data in executable_body:
                Executable.__create(result, script, data)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            result.append(FindExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            result.append(InsertExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            result.append(UpdateExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_DELETE:
            result.append(DeleteExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD:
            result.append(FileUploadExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD:
            result.append(FileDownloadExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES:
            result.append(FilePropertiesExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_HASH:
            result.append(FileHashExecutable(script, executable_data))
