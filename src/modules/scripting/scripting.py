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
from src.modules.subscription.vault import VaultManager
from src.utils_v1.constants import SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, SCRIPTING_EXECUTABLE_TYPE_FIND, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from src.utils_v1.did_file_info import query_hash
from src.utils_v1.did_mongo_db_resource import populate_options_count_documents, convert_oid, get_mongo_database_size, \
    populate_find_options_from_body, populate_options_insert_one, populate_options_update_one
from src.utils_v1.did_scripting import populate_with_params_values, populate_file_body
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_mongodb_data
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.consts import COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_SHA256
from src.utils.db_client import cli
from src.utils.http_exception import BadRequestException, CollectionNotFoundException, ScriptNotFoundException, UnauthorizedException


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
    def __init__(self, params, user_did, app_did):
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

    def is_satisfied(self, condition_data, context) -> bool:
        """ If the caller matches the condition """
        if not condition_data:
            return True

        type_, body = condition_data['type'], condition_data['body']
        if type_ == 'or':
            return any([self.is_satisfied(data, context) for data in body])
        elif type_ == 'and':
            return all([self.is_satisfied(data, context) for data in body])

        # type: 'queryHasResults'

        col_name, col_filter = body['collection'], body.get('filter', {})
        msg = populate_with_params_values(self.user_did, self.app_did, col_filter, self.params)
        if msg:
            raise BadRequestException(msg='Cannot find parameter: ' + msg)

        col = cli.get_user_collection(context.target_did, context.target_app_did, col_name)
        if not col:
            raise BadRequestException(msg='Do not find condition collection with name ' + col_name)

        # INFO: 'options' is the internal supporting.
        options = populate_options_count_documents(body.get('options', {}))
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
            raise CollectionNotFoundException(msg='The collection scripts of target user can not be found.')
        return col.find_one({'name': script_name})


class Executable:
    """ Executable represents an action which contains operation for database and files. """

    def __init__(self, script, executable_data):
        self.script = script
        self.name = executable_data['name']
        self.body = executable_data['body']
        self.is_output = executable_data.get('output', True)
        self.is_ipfs = script.is_ipfs
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
        """ only for the body of file types """
        populate_file_body(self.body, self.get_params())
        return self.body

    def _create_transaction(self, action_type):
        """ Here just create a transaction for later uploading and downloading. """
        body = self.get_populated_file_body()

        # The created transaction record can only be use once. So do not consider run script twice.
        # If the user not call this transaction later, the transaction record will keep forever.
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
            raise BadRequestException(msg='Cannot create a new transaction.')

        update_used_storage_for_mongodb_data(self.get_target_did(),
                                             get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return {
            "transaction_id": jwt.encode({
                "row_id": data.get('inserted_id', None),
                "target_did": self.get_target_did(),
                "target_app_did": self.get_target_app_did()
            }, hive_setting.PASSWORD, algorithm='HS256')
        }

    @staticmethod
    def create_executables(script, executable_data):
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

    def __get_populated_find_options(self):
        options = populate_find_options_from_body(self.body)
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), options, self.get_params())
        if msg:
            raise BadRequestException(msg=f'Cannot get the value of the parameters for the find options: {msg}')
        return options

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did())

        filter_ = self.get_populated_filter()
        items = cli.find_many(self.get_target_did(), self.get_target_app_did(),
                              self.get_collection_name(), filter_, self.__get_populated_find_options())
        total = cli.count(self.get_target_did(), self.get_target_app_did(), self.get_collection_name(), filter_, throw_exception=False)

        return self.get_output_data({'total': total, 'items': json.loads(json_util.dumps(items))})


class InsertExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        self.vault_manager.get_vault(self.get_target_did()).check_storage()

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
        self.vault_manager.get_vault(self.get_target_did()).check_storage()

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
        self.vault_manager.get_vault(self.get_target_did())

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
        return self._create_transaction('upload')


class FileDownloadExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self._create_transaction('download')


class FilePropertiesExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        body = self.get_populated_file_body()
        logging.info(f'get file properties: is_ipfs={self.is_ipfs}, path={body["path"]}')

        doc = self.ipfs_files.get_file_metadata(self.get_target_did(), self.get_target_app_did(), body['path'])
        return self.get_output_data({
            "type": "file" if doc[COL_IPFS_FILES_IS_FILE] else "folder",
            "name": body['path'],
            "size": doc[SIZE],
            "last_modify": doc['modified']
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
    """ Represents a script registered by owner and ran by caller.
    Their user DIDs can be same or not, or even the caller is anonymous.

    .. Parameter Replacement ( $params )

    The following format can be defined on the value of script elements
    which includes: condition ( filter ), executable ( as the following details ).

    Database types::

        find: filter, options;
        insert: document;
        update: filter, update;
        delete: filter;

    File types::

        'path';

    Parameter definition::

        "$params.<parameter name>"

    Example of key-value::

        "group": "$params.group"  # the $param definition MUST the whole part of the value

    For the 'path' parameter of file types, the following patterns also support::

        "path": "/data/$params.file_name"  # the $param definition can be as the part of the path

        "path": "/data/${params.folder_name}/avatar.png"  # another form for the $param definition

    .. allowAnonymousUser, allowAnonymousApp

    These two options is for first checking when caller calls the script.

    allowAnonymousUser=True, allowAnonymousApp=True
        Caller can run the script without 'access token'.

    others
        Caller can run the script with 'access token'.

    """
    DOLLAR_REPLACE = '%%'

    def __init__(self, script_name, run_data, user_did, app_did, scripting=None, is_ipfs=False):
        self.user_did = user_did
        self.app_did = app_did

        # The script content will be got by 'self.name' dynamically.
        # Keeping the script name and running data is enough
        self.name = script_name
        self.context = Context(run_data.get('context', None) if run_data else None, user_did, app_did)
        self.params = run_data.get('params', None) if run_data else None

        self.scripting = scripting

        # TODO: to be removed
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

        # The feature support that the script can be run without access token when two anonymous options are all True
        anonymous_access = script_data.get('allowAnonymousUser', False) and script_data.get('allowAnonymousApp', False)
        if not anonymous_access and g.token_error is not None:
            raise UnauthorizedException(msg=f'Parse access token for running script error: {g.token_error}')

        # Reverse the script content to let the key contains '$'
        Script.fix_dollar_keys_recursively(script_data, is_save=False)

        # condition checking for all executables
        condition = Condition(self.params, self.user_did, self.app_did)
        if not condition.is_satisfied(script_data.get('condition'), self.context):
            raise BadRequestException(msg="Caller can't match the condition.")

        # run executables and get the results
        executables = Executable.create_executables(self, script_data['executable'])
        return list(filter(lambda r: r, [e.execute() for e in executables]))

    @staticmethod
    def fix_dollar_keys_recursively(data, is_save=True):
        """ Used for registering script content to skip $ restrictions in the field name of the document.

        Recursively replace the key from '$' to '%%' or backward.
        
        :param data: dict | list
        :param is_save: True means trying to save the data (script content) to mongo database, else means loading.
        """
        src = '$' if is_save else Script.DOLLAR_REPLACE
        dst = Script.DOLLAR_REPLACE if is_save else '$'
        if type(data) is dict:
            for key in list(data.keys()):
                if key.startswith(src):
                    new_key = dst + key[len(src):]
                    data[new_key] = data.pop(key)
                else:
                    new_key = key
                Script.fix_dollar_keys_recursively(data[new_key], is_save=is_save)
        elif type(data) is list:
            for v in data:
                Script.fix_dollar_keys_recursively(v, is_save=is_save)


class Scripting:
    def __init__(self, is_ipfs=False):
        self.files = None
        self.is_ipfs = is_ipfs
        self.ipfs_files = IpfsFiles()
        self.vault_manager = VaultManager()

    def set_script(self, script_name):
        self.vault_manager.get_vault(g.usr_did).check_storage()

        json_data = request.get_json(force=True, silent=True)
        Script.validate_script_data(json_data)

        result = self.__upsert_script_to_database(script_name, json_data, g.usr_did, g.app_did)
        update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))
        return result

    def set_script_for_anonymous_file(self, script_name: str, file_path: str):
        """ set script for uploading public file """
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
        Script.fix_dollar_keys_recursively(json_data)
        ret = col.replace_one({"name": script_name}, convert_oid(json_data),
                              upsert=True, bypass_document_validation=False)
        return {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id) if ret.upserted_id else '',
        }

    def delete_script(self, script_name):
        self.vault_manager.get_vault(g.usr_did)

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

    def upload_file(self, transaction_id):
        return self.handle_transaction(transaction_id)

    def handle_transaction(self, transaction_id, is_download=False):
        """ Do real uploading or downloading for caller """
        # check by transaction id from request body
        row_id, target_did, target_app_did = self.parse_transaction_id(transaction_id)
        col_filter = {"_id": ObjectId(row_id)}
        trans = cli.find_one(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, col_filter)
        if not trans:
            raise BadRequestException(msg="Cannot find the transaction by id.")

        # Do anonymous checking, it's same as 'Script.execute'
        anonymous_access = trans.get('anonymous', False)
        if not anonymous_access and g.token_error is not None:
            raise UnauthorizedException(msg=f'Parse access token for running script error: {g.token_error}')

        # executing uploading or downloading
        data = None
        logging.info(f'handle transaction by id: is_ipfs={self.is_ipfs}, '
                     f'is_download={is_download}, file_name={trans["document"]["file_name"]}')
        if is_download:
            data = self.ipfs_files.download_file_with_path(target_did, target_app_did, trans['document']['file_name'])
        else:
            # Place here because not want to change the logic for v1.
            VaultManager().get_vault(target_did).check_storage()
            self.ipfs_files.upload_file_with_path(target_did, target_app_did, trans['document']['file_name'])

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
