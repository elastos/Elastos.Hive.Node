# -*- coding: utf-8 -*-

"""
The main handling file of scripting module.
"""
import logging

import jwt
from flask import request, g
from bson import ObjectId

from src import hive_setting
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_mongodb_data
from src.utils_v1.constants import SCRIPTING_SCRIPT_COLLECTION, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from src.utils_v1.did_mongo_db_resource import populate_options_count_documents, get_mongo_database_size
from src.utils.http_exception import BadRequestException, ScriptNotFoundException, UnauthorizedException
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.modules.subscription.vault import VaultManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.scripting.executable import Executable, get_populated_value_with_params


def validate_exists(json_data, properties, parent_name=None):
    """ check the input parameters exist, support dot, such as: a.b.c

    :param json_data: dict
    :param parent_name: parent name which will find first and all are 'dict', support 'a.b.c'
                        can be None, then directly check on 'json_data'
    :param properties: properties under 'json_data'['parent_name']
    """
    if not isinstance(json_data, dict):
        raise BadRequestException(msg=f'Invalid parameter: "{str(json_data)}" (not dict)')

    # try to get the parent dict
    if not parent_name:
        data = json_data
    else:
        # get first child, if exists, recursive validate
        parts = parent_name.split('.')
        data = json_data.get(parts[0])
        if not isinstance(data, dict):
            raise BadRequestException(msg=f'Invalid parameter: "{str(json_data)}" ("{parts[0]}" is not dict)')

        validate_exists(data, properties, parent_name='.'.join(parts[1:]) if len(parts) > 1 else None)

    # directly check
    for prop in properties:
        if prop not in data:
            raise BadRequestException(msg=f'Invalid parameter: "{str(json_data)}" ("{prop}" not exist)')


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
    def __init__(self, params):
        self.user_did = g.usr_did
        self.app_did = g.app_did
        self.params = params
        self.mcli = MongodbClient()

    @staticmethod
    def validate_data(json_data):
        """ Validate the condition data, can not nest than 5 layers.
        :param json_data: condition content.
        """
        if not json_data:
            return

        def validate(data, layer):
            if layer > 5:
                raise BadRequestException(msg='Too more nested conditions.')

            validate_exists(data, ['name', 'type', 'body'])

            condition_type = data['type']
            if condition_type not in ['or', 'and', 'queryHasResults']:
                raise BadRequestException(msg=f"Unsupported condition type {condition_type}")

            if condition_type in ['and', 'or']:
                if not isinstance(data['body'], list)\
                        or not data['body']:
                    raise BadRequestException(msg=f"Condition body MUST be list "
                                                  f"and at least contain one element for the type '{condition_type}'")
                for d in data['body']:
                    validate(d, layer + 1)
            else:
                # Just 'queryHasResults'
                validate_exists(data, ['collection'], parent_name='body')

        validate(json_data, 1)

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

        col_name = body['collection']
        col_filter = get_populated_value_with_params(body.get('filter', {}), self.user_did, self.app_did, self.params)
        # INFO: 'options' is the internal supporting.
        options = populate_options_count_documents(body.get('options', {}))

        col = self.mcli.get_user_collection(context.target_did, context.target_app_did, col_name)
        return col.count(col_filter, **options) > 0


class Context:
    def __init__(self, context_data):
        self.user_did, self.app_did = g.usr_did, g.app_did

        # default is caller's DID
        self.target_did, self.target_app_did = g.usr_did, g.app_did
        if context_data:
            self.target_did = context_data['target_did']
            self.target_app_did = context_data['target_app_did']

        self.mcli = MongodbClient()

    @staticmethod
    def validate_data(json_data):
        if not json_data:
            return

        target_did = json_data.get('target_did')
        target_app_did = json_data.get('target_app_did')
        if not target_did or not target_app_did:
            raise BadRequestException(msg='target_did or target_app_did MUST be set.')

    def check_target_dids(self):
        """ add this check because of supporting anonymously running script """
        if not self.target_did or not self.target_app_did:
            raise BadRequestException(msg=f"target_did and target_app_did MUST be provided when do anonymous access.")

    def get_script_data(self, script_name):
        """ get the script data by target_did and target_app_did """
        col = self.mcli.get_user_collection(self.target_did, self.target_app_did, SCRIPTING_SCRIPT_COLLECTION, create_on_absence=True)
        return col.find_one({'name': script_name})


class Script:
    """ Represents a script registered by owner and ran by caller.
    Their user DIDs can be same or not, or even the caller is anonymous.

    .. allowAnonymousUser, allowAnonymousApp

    These two options is for first checking when caller calls the script.

    allowAnonymousUser=True, allowAnonymousApp=True
        Caller can run the script without 'access token'.

    others
        Caller can run the script with 'access token'.


    .. context

    The context which used to specify the owner of script contains the two items:

        target_did
        target_app_did

    If not specified, relating did of caller will be used.


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

        # the $param definition MUST the whole part of the value
        "group": "$params.group"

    For the 'path' parameter of file types, the following patterns also support::

        # the $param definition can be as the part of the path
        "path": "/data/$params.file_name"

        # another form for the $param definition
        "path": "/data/${params.folder_name}/avatar.png"

    """
    DOLLAR_REPLACE = '%%'

    def __init__(self, script_name, run_data, scripting=None):
        self.user_did = g.usr_did
        self.app_did = g.app_did

        # The script content will be got by 'self.name' dynamically.
        # Keeping the script name and running data is enough
        self.name = script_name
        self.context = Context(run_data.get('context', None) if run_data else None)
        self.params = run_data.get('params', None) if run_data else None

        # for file uploading and downloading
        self.anonymous_app = self.anonymous_user = False

        self.scripting = scripting

    @staticmethod
    def validate_script_data(json_data):
        """ json_data: script content """
        if not json_data:
            raise BadRequestException(msg="Script definition can't be empty.")

        validate_exists(json_data, ['executable'])

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
        self.context.check_target_dids()

        script_data = self.context.get_script_data(self.name)
        if not script_data:
            raise BadRequestException(msg=f"Can't get the script with name '{self.name}'")

        self.anonymous_app = script_data.get('allowAnonymousUser', False)
        self.anonymous_user = script_data.get('allowAnonymousApp', False)

        # The feature support that the script can be run without access token when two anonymous options are all True
        anonymous_access = self.anonymous_app and self.anonymous_user
        if not anonymous_access and g.token_error is not None:
            raise UnauthorizedException(msg=f'Parse access token for running script error: {g.token_error}')

        # Reverse the script content to let the key contains '$'
        Script.fix_dollar_keys_recursively(script_data, is_save=False)

        # condition checking for all executables
        condition = Condition(self.params)
        if not condition.is_satisfied(script_data.get('condition'), self.context):
            raise BadRequestException(msg="Caller can't match the condition.")

        # run executables and get the results
        executables: [Executable] = Executable.create_executables(self, script_data['executable'])
        # executable_name: executable_result ( MUST not None ), this is for the executable option 'is_out'
        return {k: v for k, v in {e.name: e.execute() for e in executables}.items() if v is not None}

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
    def __init__(self):
        self.files = None
        self.ipfs_files = IpfsFiles()
        self.vault_manager = VaultManager()
        self.mcli = MongodbClient()

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
        self.__upsert_script_to_database(script_name, json_data, g.usr_did, g.app_did)
        update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))

    def __upsert_script_to_database(self, script_name, json_data, user_did, app_did):
        Script.fix_dollar_keys_recursively(json_data)
        json_data['name'] = script_name

        col = self.mcli.get_user_collection(user_did, app_did, SCRIPTING_SCRIPT_COLLECTION, create_on_absence=True)
        return col.replace_one({"name": script_name}, json_data)

    def delete_script(self, script_name):
        self.vault_manager.get_vault(g.usr_did)

        col = self.mcli.get_user_collection(g.usr_did, g.app_did, SCRIPTING_SCRIPT_COLLECTION, create_on_absence=True)
        result = col.delete_one({'name': script_name})

        if result['deleted_count'] > 0:
            update_used_storage_for_mongodb_data(g.usr_did, get_mongo_database_size(g.usr_did, g.app_did))
        else:
            raise ScriptNotFoundException(f'The script {script_name} does not exist.')

    def run_script(self, script_name):
        json_data = request.get_json(force=True, silent=True)
        Script.validate_run_data(json_data)
        return Script(script_name, json_data, scripting=self).execute()

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
        return Script(script_name, json_data, scripting=self).execute()

    def upload_file(self, transaction_id):
        return self.handle_transaction(transaction_id)

    def handle_transaction(self, transaction_id, is_download=False):
        """ Do real uploading or downloading for caller """
        # check by transaction id from request body
        row_id, target_did, target_app_did = self.parse_transaction_id(transaction_id)
        col_filter = {"_id": ObjectId(row_id)}
        col = self.mcli.get_user_collection(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, create_on_absence=True)
        trans = col.find_one({"_id": ObjectId(row_id)})

        # Do anonymous checking, it's same as 'Script.execute'
        anonymous_access = trans.get('anonymous', False)
        if not anonymous_access and g.token_error is not None:
            raise UnauthorizedException(msg=f'Parse access token for running script error: {g.token_error}')

        # executing uploading or downloading
        data = None
        logging.info(f'handle transaction by id: is_download={is_download}, file_name={trans["document"]["file_name"]}')
        if is_download:
            data = self.ipfs_files.download_file_with_path(target_did, target_app_did, trans['document']['file_name'])
        else:
            # Place here because not want to change the logic for v1.
            VaultManager().get_vault(target_did).check_storage()
            self.ipfs_files.upload_file_with_path(target_did, target_app_did, trans['document']['file_name'])

        # recalculate the storage usage of the database
        col.delete_many(col_filter)
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
