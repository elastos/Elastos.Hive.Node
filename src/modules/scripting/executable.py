from src.utils_v1.constants import SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_EXECUTABLE_TYPE_INSERT, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_CALLER_DID, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID, SCRIPTING_EXECUTABLE_PARAMS
from src.utils.http_exception import BadRequestException
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.modules.subscription.vault import VaultManager


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

    def populate_value(v):
        if isinstance(v, dict):
            return get_populated_value_with_params(v, user_did, app_did, params)
        elif isinstance(v, list):  # tuple can not change the element, so skip
            return get_populated_value_with_params(v, user_did, app_did, params)
        elif isinstance(v, str):
            if v == SCRIPTING_EXECUTABLE_CALLER_DID:
                return user_did
            elif v == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                return app_did
            elif v.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                p = v.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if p not in params:
                    raise BadRequestException(f'Can not find parameter "{p}" for the script.')
                return params[p]
            return v
        else:
            return v

    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = populate_value(v)
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
    def validate_data(json_data, can_aggregated=True):
        """ Note: type 'aggregated' can not contain same type.

        :param can_aggregated: recursive option.
        :param json_data: executable data (dict)
        """
        from src.modules.scripting.scripting import validate_exists

        # validate first layer members
        validate_exists(json_data, ['name', 'type', 'body'])

        # validate 'type'
        types = [SCRIPTING_EXECUTABLE_TYPE_FIND,
                 SCRIPTING_EXECUTABLE_TYPE_INSERT,
                 SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                 SCRIPTING_EXECUTABLE_TYPE_DELETE,
                 SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                 SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                 SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                 SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]
        if can_aggregated:
            types.append(SCRIPTING_EXECUTABLE_TYPE_AGGREGATED)

        if json_data['type'] not in types:
            raise BadRequestException(msg=f"Invalid type {json_data['type']} of the executable.")

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            items = json_data['body']
            if not isinstance(items, list or len(items) < 1):
                raise BadRequestException(msg=f"Executable body MUST be list for type "
                                              f"'{SCRIPTING_EXECUTABLE_TYPE_AGGREGATED}'.")

            for item in items:
                Executable.validate_data(item, can_aggregated=False)

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FIND,
                                 SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                 SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                 SCRIPTING_EXECUTABLE_TYPE_DELETE]:
            validate_exists(json_data['body'], ['collection'])

            if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_INSERT:
                validate_exists(json_data['body'], ['document'])

            if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
                validate_exists(json_data['body'], ['update'])

            if 'options' in json_data['body'] and not isinstance(json_data['body']['options'], dict):
                raise BadRequestException(msg=f'The "options" MUST be dictionary.')

        elif json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            validate_exists(json_data['body'], ['path'])

            path = json_data['body']['path']
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
        from src.modules.scripting.database_executable import FindExecutable, InsertExecutable, UpdateExecutable, DeleteExecutable
        from src.modules.scripting.file_executable import FileUploadExecutable, FileDownloadExecutable, FilePropertiesExecutable, FileHashExecutable

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
