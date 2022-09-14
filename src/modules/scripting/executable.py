from src.utils.consts import SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_EXECUTABLE_TYPE_INSERT, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_CALLER_DID, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID, SCRIPTING_EXECUTABLE_PARAMS, SCRIPTING_EXECUTABLE_TYPE_COUNT
from src.utils.http_exception import NotImplementedException, InvalidParameterException
from src.modules.database.mongodb_client import MongodbClient
from src.modules.files.files_service import IpfsFiles
from src.modules.subscription.vault import VaultManager


def validate_exists(json_data, properties, parent_name=None):
    """ check the input parameters exist, support dot, such as: a.b.c

    :param json_data: dict
    :param parent_name: parent name which will find first and all are 'dict', support 'a.b.c'
                        can be None, then directly check on 'json_data'
    :param properties: properties under 'json_data'['parent_name']
    """
    if not isinstance(json_data, dict):
        raise InvalidParameterException(f'Invalid parameter: "{str(json_data)}" (not dict)')

    # try to get the parent dict
    if not parent_name:
        data = json_data
    else:
        # get first child, if exists, recursive validate
        parts = parent_name.split('.')
        data = json_data.get(parts[0])
        if not isinstance(data, dict):
            raise InvalidParameterException(f'Invalid parameter: "{str(json_data)}" ("{parts[0]}" is not dict)')

        validate_exists(data, properties, parent_name='.'.join(parts[1:]) if len(parts) > 1 else None)

    # directly check
    for prop in properties:
        if prop not in data:
            raise InvalidParameterException(f'Invalid parameter: "{str(json_data)}" ("{prop}" not exist)')


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

    def populate_value(value):
        if isinstance(value, dict):
            return get_populated_value_with_params(value, user_did, app_did, params)
        elif isinstance(value, list):  # tuple can not change the element, so skip
            return get_populated_value_with_params(value, user_did, app_did, params)
        elif isinstance(value, str):
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                if not user_did:
                    raise InvalidParameterException(f"Can not find caller's 'user_did' as '$caller_did' exists in script.")
                return user_did
            elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                if not app_did:
                    raise InvalidParameterException(f"Can not find caller's 'app_did' as '$caller_app_did' exists in script.")
                return app_did
            elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                p = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if p not in params:
                    raise InvalidParameterException(f'Can not find "{p}" of "params" for the script.')
                return params[p]
            return value
        else:
            return value

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

        # If execute this executable with output or not.
        self.output = executable_data.get('output', True)

        self.ipfs_files = IpfsFiles()
        self.vault_manager = VaultManager()
        self.mcli = MongodbClient()

    def execute(self):
        # Override
        raise NotImplementedException()

    def get_user_did(self):
        return self.script.user_did

    def get_app_did(self):
        return self.script.app_did

    def get_target_did(self):
        return self.script.context.target_did

    def get_target_app_did(self):
        return self.script.context.target_app_did

    def get_params(self):
        return self.script.params

    def get_result_data(self, data):
        """ for response with the option 'is_output' of the executable """
        return data if self.output else None

    @staticmethod
    def validate_data(json_data, can_aggregated=True):
        """ Note: type 'aggregated' can not contain same type.

        :param can_aggregated: recursive option.
        :param json_data: executable data (dict)
        """
        # validate first layer members
        validate_exists(json_data, ['name', 'type', 'body'])

        # validate 'type'
        types = [SCRIPTING_EXECUTABLE_TYPE_FIND,
                 SCRIPTING_EXECUTABLE_TYPE_COUNT,
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
            raise InvalidParameterException(f"Invalid type {json_data['type']} of the executable.")

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            items = json_data['body']
            if not isinstance(items, list or len(items) < 1):
                raise InvalidParameterException(f"Executable body MUST be list for type "
                                                f"'{SCRIPTING_EXECUTABLE_TYPE_AGGREGATED}'.")

            for item in items:
                Executable.validate_data(item, can_aggregated=False)

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FIND,
                                 SCRIPTING_EXECUTABLE_TYPE_COUNT,
                                 SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                 SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                 SCRIPTING_EXECUTABLE_TYPE_DELETE]:
            validate_exists(json_data['body'], ['collection'])

            if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_INSERT:
                validate_exists(json_data['body'], ['document'])
            elif json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
                validate_exists(json_data['body'], ['update'])

            if 'filter' in json_data['body'] and not isinstance(json_data['body']['filter'], dict):
                raise InvalidParameterException(f'The "filter" MUST be dictionary.')

            if 'options' in json_data['body'] and not isinstance(json_data['body']['options'], dict):
                raise InvalidParameterException(f'The "options" MUST be dictionary.')

        elif json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                   SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            validate_exists(json_data['body'], ['path'])

            path = json_data['body']['path']
            if not path or not isinstance(path, str):
                raise InvalidParameterException(f'Invalid parameter "path" {json_data}')

    @staticmethod
    def create_executables(script, executable_data) -> ['Executable']:
        result = []
        Executable.__create(result, script, executable_data)
        return result

    @staticmethod
    def __create(result, script, executable_data):
        from src.modules.scripting.database_executable import FindExecutable, InsertExecutable, UpdateExecutable, DeleteExecutable, CountExecutable
        from src.modules.scripting.file_executable import FileUploadExecutable, FileDownloadExecutable, FilePropertiesExecutable, FileHashExecutable

        executable_type = executable_data['type']
        executable_body = executable_data['body']
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for data in executable_body:
                Executable.__create(result, script, data)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            result.append(FindExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_COUNT:
            result.append(CountExecutable(script, executable_data))
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
