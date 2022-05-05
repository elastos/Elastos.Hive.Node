# -*- coding: utf-8 -*-

"""
The main handling file of scripting module.
"""
import json
import logging

import jwt
from flask import request, g
from bson import ObjectId, json_util

from src import hive_setting
from src.utils_v1.constants import SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, SCRIPTING_EXECUTABLE_TYPE_FIND, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, VAULT_ACCESS_R, VAULT_ACCESS_WR, VAULT_ACCESS_DEL
from src.utils_v1.did_file_info import query_upload_get_filepath, query_hash
from src.utils_v1.did_mongo_db_resource import populate_options_count_documents, convert_oid, get_mongo_database_size, \
    populate_find_options_from_body, populate_options_insert_one, populate_options_update_one
from src.utils_v1.did_scripting import populate_with_params_values, populate_file_body
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_mongodb_data
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.consts import COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_SHA256
from src.utils.db_client import cli
from src.utils.http_exception import BadRequestException, CollectionNotFoundException, ScriptNotFoundException


def validate_exists(json_data, parent_name, prop_list):
    """ check the input parameters exist, support dot, such as: a.b.c """
    for prop in prop_list:
        parts = prop.split('.')
        prop_name = parent_name + '.' + parts[0] if parent_name else parts[0]
        if len(parts) > 1:
            validate_exists(json_data[parts[0]], prop_name, '.'.join(parts[1:]))
        else:
            if not json_data.get(prop, None):
                raise BadRequestException(msg=f'Parameter {prop_name} MUST be provided')


def fix_dollar_keys(data, is_save=True):
    """ use this because of mongo not support key starts with $ """
    if type(data) is not dict:
        return

    src = '$set' if is_save else '"$"set'
    dst = '"$"set' if is_save else '$set'
    for k, v in list(data.items()):
        if k == src:
            data[dst] = data.pop(k)

    for k, v in data.items():
        if type(v) is dict:
            fix_dollar_keys(v, is_save)
        elif type(v) is list:
            for item in v:
                fix_dollar_keys(item, is_save)


class Condition:
    def __init__(self, condition_data, params, user_did, app_did):
        self.condition_data = condition_data if condition_data else {}
        self.params = params
        self.user_did = user_did
        self.app_did = app_did

    @staticmethod
    def validate_data(json_data):
        if not json_data:
            return
        Condition.__validate_type(json_data, 1)

    @staticmethod
    def __validate_type(json_data, layer):
        if layer > 5:
            raise BadRequestException(msg='Too more nested conditions.')

        validate_exists(json_data, 'condition', ['name', 'type', 'body'])

        condition_type = json_data['type']
        if condition_type not in ['or', 'and', 'queryHasResults']:
            raise BadRequestException(msg=f"Unsupported condition type {condition_type}")

        if condition_type in ['and', 'or']:
            if not isinstance(json_data['body'], list)\
                    or not json_data['body']:
                raise BadRequestException(msg=f"Condition body MUST be list "
                                              f"and at least contain one element for the type '{condition_type}'")
            for data in json_data['body']:
                Condition.__validate_type(data, layer + 1)
        else:
            validate_exists(json_data['body'], 'condition.body', ['collection', ])

    def is_satisfied(self, context) -> bool:
        return self.__is_satisfied(self.condition_data, context)

    def __is_satisfied(self, condition_data, context) -> bool:
        if not condition_data:
            return True

        ctype = condition_data['type']
        if ctype == 'or':
            for data in condition_data['body']:
                is_sat = self.__is_satisfied(data, context)
                if is_sat:
                    return True
            return False
        elif ctype == 'and':
            for data in condition_data['body']:
                is_sat = self.__is_satisfied(data, context)
                if not is_sat:
                    return False
            return True
        else:
            return self.__is_satisfied_query_has_result(condition_data['body'], context)

    def __is_satisfied_query_has_result(self, con_body_data, context):
        col_name = con_body_data['collection']
        col_filter = con_body_data.get('filter', {})
        msg = populate_with_params_values(self.user_did, self.app_did, col_filter, self.params)
        if msg:
            raise BadRequestException(msg='Cannot find parameter: ' + msg)

        col = cli.get_user_collection(context.target_did, context.target_app_did, col_name)
        if not col:
            raise BadRequestException(msg='Do not find condition collection with name ' + col_name)

        # INFO: 'options' is the internal supporting.
        options = populate_options_count_documents(con_body_data.get('options', {}))
        return col.count_documents(convert_oid(col_filter), **options) > 0


class Context:
    def __init__(self, context_data, user_did, app_did):
        self.user_did, self.app_did = user_did, app_did
        self.target_did = user_did
        self.target_app_did = app_did
        if context_data:
            self.target_did = context_data['target_did']
            self.target_app_did = context_data['target_app_did']

    @staticmethod
    def validate_data(json_data):
        if not json_data:
            return

        target_did = json_data.get('target_did')
        target_app_did = json_data.get('target_app_did')
        if not target_did or not target_app_did:
            raise BadRequestException(msg='target_did or target_app_did MUST be set.')

    def get_script_data(self, script_name):
        """ get the script data by target_did and target_app_did """
        col = cli.get_user_collection(self.target_did, self.target_app_did, SCRIPTING_SCRIPT_COLLECTION)
        if not col:
            raise CollectionNotFoundException(msg='The collection scripts can not be found.')
        return col.find_one({'name': script_name})

    def can_anonymous_access(self, anonymous_user: bool, anonymous_app: bool):
        """ check the script option of 'anonymous_user' and 'anonymous_app' """
        if not anonymous_user and not anonymous_app:
            return self.user_did == self.target_did and self.app_did == self.target_app_did
        elif not anonymous_user and anonymous_app:
            return self.user_did == self.target_did
        elif anonymous_user and not anonymous_app:
            return self.app_did == self.target_app_did
        else:
            return True


class Executable:
    def __init__(self, script, executable_data):
        self.script = script
        self.name = executable_data['name']
        self.body = executable_data['body']
        self.is_output = executable_data.get('output', True)
        self.is_ipfs = script.is_ipfs
        self.ipfs_files = IpfsFiles()

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

    def execute(self):
        pass

    def get_did(self):
        return self.script.user_did

    def get_app_id(self):
        return self.script.app_did

    def get_target_did(self):
        return self.script.context.target_did

    def get_target_app_did(self):
        return self.script.context.target_app_did

    def get_collection_name(self):
        return self.body['collection']

    def get_filter(self):
        return self.body.get('filter', {})

    def get_context(self):
        return self.script.context

    def get_document(self):
        return self.body.get('document', {})

    def get_update(self):
        return self.body.get('update', {})

    def get_params(self):
        return self.script.params

    def get_output_data(self, data):
        return data if self.is_output else None

    def get_populated_filter(self):
        col_filter = self.get_filter()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), col_filter, self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable filter: ' + msg)
        return col_filter

    def get_populated_file_body(self):
        populate_file_body(self.body, self.get_params())
        return self.body

    def _create_transaction(self, permission, action_type):
        cli.check_vault_access(self.get_target_did(), permission)

        body = self.get_populated_file_body()
        anonymous_url = ''
        if self.is_ipfs:
            if action_type == 'download':
                metadata = self.ipfs_files.get_file_metadata(self.get_target_did(),
                                                             self.get_target_app_did(),
                                                             body['path'])
                anonymous_url = self.ipfs_files.get_ipfs_file_access_url(metadata)
        else:
            _, err = query_upload_get_filepath(self.get_target_did(), self.get_target_app_did(), body['path'])
            if err:
                raise BadRequestException(msg='Cannot get file full path with error message: ' + str(err))

        # INFO: Do not consider run script twice.
        data = cli.insert_one(self.get_target_did(),
                              self.get_target_app_did(),
                              SCRIPTING_SCRIPT_TEMP_TX_COLLECTION,
                              {
                                  "document": {
                                      "file_name": body['path'],
                                      "fileapi_type": action_type
                                  },
                                  'anonymous': self.script.anonymous_app and self.script.anonymous_user
                              }, create_on_absence=True)
        if not data.get('inserted_id', None):
            raise BadRequestException(msg='Cannot retrieve the transaction ID.')

        update_used_storage_for_mongodb_data(self.get_target_did(),
                                             get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        result = {
            "transaction_id": jwt.encode({
                "row_id": data.get('inserted_id', None),
                "target_did": self.get_target_did(),
                "target_app_did": self.get_target_app_did()
            }, hive_setting.PASSWORD, algorithm='HS256')
        }
        if action_type == 'download' and self.is_ipfs and self.script.anonymous_app and self.script.anonymous_user:
            result['anonymous_url'] = anonymous_url
        return result

    @staticmethod
    def create(script, executable_data):
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


class FindExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_R)
        items = cli.find_many(self.get_target_did(), self.get_target_app_did(),
                              self.get_collection_name(), self.get_populated_filter(), populate_find_options_from_body(self.body))
        return self.get_output_data({"items": json.loads(json_util.dumps(items))})


class InsertExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_WR)

        document = self.get_document()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), document, self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable document: ' + msg)

        data = cli.insert_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              document,
                              populate_options_insert_one(self.body))

        update_used_storage_for_mongodb_data(self.get_did(),
                                             get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class UpdateExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_WR)

        col_update = self.get_update()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), col_update.get('$set'), self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable update: ' + msg)

        data = cli.update_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              self.get_populated_filter(),
                              col_update,
                              populate_options_update_one(self.body))

        update_used_storage_for_mongodb_data(self.get_did(),
                                             get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class DeleteExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_DEL)

        data = cli.delete_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              self.get_populated_filter())

        update_used_storage_for_mongodb_data(self.get_did(),
                                         get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class FileUploadExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self._create_transaction(VAULT_ACCESS_WR, 'upload')


class FileDownloadExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self._create_transaction(VAULT_ACCESS_R, 'download')


class FilePropertiesExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        body = self.get_populated_file_body()
        logging.info(f'get file properties: is_ipfs={self.is_ipfs}, path={body["path"]}')
        if self.is_ipfs:
            doc = self.ipfs_files.get_file_metadata(self.get_target_did(), self.get_target_app_did(), body['path'])
            return self.get_output_data({
                "type": "file" if doc[COL_IPFS_FILES_IS_FILE] else "folder",
                "name": body['path'],
                "size": doc[SIZE],
                "last_modify": doc['modified']
            })
        full_path, stat = self.script.scripting\
            .get_files().get_file_stat_by_did(self.get_target_did(), self.get_target_app_did(), body['path'])
        return self.get_output_data({
            "type": "file" if full_path.is_file() else "folder",
            "name": body['path'],
            "size": stat.st_size,
            "last_modify": stat.st_mtime
        })


class FileHashExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        body = self.get_populated_file_body()
        logging.info(f'get file hash: is_ipfs={self.is_ipfs}, path={body["path"]}')
        if self.is_ipfs:
            doc = self.ipfs_files.get_file_metadata(self.get_target_did(), self.get_target_app_did(), body['path'])
            return self.get_output_data({"SHA256": doc[COL_IPFS_FILES_SHA256]})
        data, err = query_hash(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException(msg='Failed to get file hash code with error message: ' + str(err))
        return self.get_output_data(data)


class Script:
    DOLLAR_REPLACE = '%%'

    def __init__(self, script_name, run_data, user_did, app_did, scripting=None, is_ipfs=False):
        self.user_did = user_did
        self.app_did = app_did
        self.name = script_name
        self.context = Context(run_data.get('context', None) if run_data else None, user_did, app_did)
        self.params = run_data.get('params', None) if run_data else None
        self.condition = None
        self.executables = []
        self.anonymous_user = False
        self.anonymous_app = False
        self.scripting = scripting
        self.is_ipfs = is_ipfs

    @staticmethod
    def validate_script_data(json_data):
        if not json_data:
            raise BadRequestException(msg="Script definition can't be empty.")

        validate_exists(json_data, '', ['executable', ])

        Condition.validate_data(json_data.get('condition', None))
        Executable.validate_data(json_data['executable'])

    @staticmethod
    def validate_run_data(json_data):
        """ context, params may not exist. """
        if not json_data:
            return

        Context.validate_data(json_data.get('context', None))

    def execute(self):
        """
        Run executables and return response data for the executable which output option is true.
        """
        script_data = self.context.get_script_data(self.name)
        if not script_data:
            raise BadRequestException(msg=f"Can't get the script with name '{self.name}'")
        Script.fixDollarKeysRecursively(script_data, is_save=False)
        self.executables = Executable.create(self, script_data['executable'])
        self.anonymous_user = script_data.get('allowAnonymousUser', False)
        self.anonymous_app = script_data.get('allowAnonymousApp', False)

        result = dict()
        for executable in self.executables:
            self.condition = Condition(script_data.get('condition'),
                                       executable.get_params(), self.user_did, self.app_did)
            if not self.context.can_anonymous_access(self.anonymous_user, self.anonymous_app) \
                    and not self.condition.is_satisfied(self.context):
                raise BadRequestException(msg="Caller can't match the condition or access anonymously for the script.")

            ret = executable.execute()
            if ret:
                result[executable.name] = ret

        return result

    @staticmethod
    def fixDollarKeysRecursively(iterable, is_save=True):
        """ Used for registering script content to skip $ restrictions in the field name of the document.
        Recursively replace the key which start with 'src' to 'dst'.
        """
        src = '$' if is_save else Script.DOLLAR_REPLACE
        dst = Script.DOLLAR_REPLACE if is_save else '$'
        if type(iterable) is dict:
            for key in list(iterable.keys()):
                if key.startswith(src):
                    new_key = dst + key[len(src):]
                    iterable[new_key] = iterable.pop(key)
                else:
                    new_key = key
                Script.fixDollarKeysRecursively(iterable[new_key], is_save=is_save)
        elif type(iterable) is list:
            for v in iterable:
                Script.fixDollarKeysRecursively(v, is_save=is_save)


class Scripting:
    def __init__(self, is_ipfs=False):
        self.files = None
        self.is_ipfs = is_ipfs
        self.ipfs_files = IpfsFiles()

    def set_script(self, script_name):
        cli.check_vault_access(g.usr_did, VAULT_ACCESS_WR)

        json_data = request.get_json(force=True, silent=True)
        Script.validate_script_data(json_data)

        result = self.__upsert_script_to_database(script_name, json_data, g.usr_did, g.app_did)
        update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))
        return result

    def set_script_for_anonymous_file(self, script_name: str, file_path: str):
        json_data = {
            "executable": {
                "output": True,
                "name": script_name,
                "type": "fileDownload",
                "body": {
                    "path": file_path
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        }
        result = self.__upsert_script_to_database(script_name, json_data, g.usr_did, g.app_did)
        update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))

    def __upsert_script_to_database(self, script_name, json_data, user_did, app_did):
        col = cli.get_user_collection(user_did, app_did, SCRIPTING_SCRIPT_COLLECTION, create_on_absence=True)
        json_data['name'] = script_name
        Script.fixDollarKeysRecursively(json_data)
        ret = col.replace_one({"name": script_name}, convert_oid(json_data),
                              upsert=True, bypass_document_validation=False)
        return {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id) if ret.upserted_id else '',
        }

    def delete_script(self, script_name):
        cli.check_vault_access(g.usr_did, VAULT_ACCESS_DEL)

        col = cli.get_user_collection(g.usr_did, g.app_did, SCRIPTING_SCRIPT_COLLECTION, create_on_absence=True)

        ret = col.delete_many({'name': script_name})
        if ret.deleted_count > 0:
            update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))
        else:
            raise ScriptNotFoundException(f'The script {script_name} does not exist.')

    def run_script(self, script_name):
        json_data = request.get_json(force=True, silent=True)
        Script.validate_run_data(json_data)
        return Script(script_name, json_data, g.usr_did, g.app_did, scripting=self, is_ipfs=self.is_ipfs).execute()

    def run_script_url(self, script_name, target_did, target_app_did, params):
        json_data = {
            'params': params
        }
        if target_did and target_app_did:
            json_data['context'] = {
                'target_did': target_did,
                'target_app_did': target_app_did
            }
        Script.validate_run_data(json_data)
        return Script(script_name, json_data, g.usr_did, g.app_did, scripting=self, is_ipfs=self.is_ipfs).execute()

    def get_files(self):
        if not self.files:
            from src.modules.deprecated.files import Files
            self.files = Files()
        return self.files

    def upload_file(self, transaction_id):
        return self.handle_transaction(transaction_id)

    def handle_transaction(self, transaction_id, is_download=False):
        # check by transaction id
        row_id, target_did, target_app_did = self.parse_transaction_id(transaction_id)
        col_filter = {"_id": ObjectId(row_id)}
        trans = cli.find_one(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, col_filter)
        if not trans:
            raise BadRequestException(msg="Cannot find the transaction by id.")

        # executing uploading or downloading
        data = None
        logging.info(f'handle transaction by id: is_ipfs={self.is_ipfs}, '
                     f'is_download={is_download}, file_name={trans["document"]["file_name"]}')
        if self.is_ipfs:
            if is_download:
                data = self.ipfs_files.download_file_with_path(target_did, target_app_did, trans['document']['file_name'])
            else:
                self.ipfs_files.upload_file_with_path(target_did, target_app_did, trans['document']['file_name'])
        else:
            if is_download:
                data = self.get_files().download_file_by_did(target_did, target_app_did, trans['document']['file_name'])
            else:
                self.get_files().upload_file_by_did(target_did, target_app_did, trans['document']['file_name'])

        # recalculate the storage usage of the database
        cli.delete_one(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, col_filter)
        update_used_storage_for_mongodb_data(target_did, get_mongo_database_size(target_did, target_app_did))

        # return the content of the file
        return data

    def download_file(self, transaction_id):
        return self.handle_transaction(transaction_id, is_download=True)

    def parse_transaction_id(self, transaction_id):
        try:
            trans = jwt.decode(transaction_id, hive_setting.PASSWORD, algorithms=['HS256'])
            return trans.get('row_id', None), trans.get('target_did', None), trans.get('target_app_did', None)
        except Exception as e:
            raise BadRequestException(msg=f"Invalid transaction id '{transaction_id}'")
