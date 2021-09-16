# -*- coding: utf-8 -*-

"""
The entrance for ipfs-backup module.
"""
import threading

from flask import request

from src.modules.auth.auth import Auth
from src.utils.consts import BACKUP_REQUEST_TYPE, BACKUP_REQUEST_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_PROCESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.http_exception import InvalidParameterException, BadRequestException
from src.utils.http_response import hive_restful_response
from src.utils_v1.constants import VAULT_ACCESS_R, DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, USER_DID


class ExecutorBase(threading.Thread):
    def __init__(self):
        super().__init__()


class BackupExecutor(ExecutorBase):
    def __init__(self):
        super().__init__()

    def run(self):
        pass


class RestoreExecutor(ExecutorBase):
    def __init__(self):
        super().__init__()

    def run(self):
        pass


class IpfsBackupClient:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting
        self.auth = Auth(app, hive_setting)

    @hive_restful_response
    def get_state(self):
        did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        return self.get_state_from_request(did)

    @hive_restful_response
    def backup(self, credential):
        did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.check_state_for_backup_or_restore()
        self.save_request(did, credential, credential_info)
        BackupExecutor().start()

    @hive_restful_response
    def restore(self, credential):
        did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.check_state_for_backup_or_restore(did)
        self.save_request(did, credential, credential_info, is_restore=True)
        RestoreExecutor().start()

    def check_state_for_backup_or_restore(self, did):
        result = self.get_state_from_request(did)
        if result['result'] == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException(msg=f'The {result["state"]} is in process. Please try later.')

    def get_state_from_request(self, did):
        state, result, msg = BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, ''
        req = self.get_request_by_did(did)
        if req:
            state = req.get(BACKUP_REQUEST_ACTION)
            result = req.get(BACKUP_REQUEST_STATE)
            msg = req.get(BACKUP_REQUEST_STATE_MSG)
            if state == BACKUP_REQUEST_ACTION_BACKUP and result == BACKUP_REQUEST_STATE_SUCCESS:
                # TODO: check the result of the backup server side.
                pass
        return {
            'state': state,
            'result': result,
            'message': msg
        }

    def get_request_by_did(self, did):
        col_filter = {USER_DID: did, BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        return cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, col_filter,
                                   is_create=True, is_raise=False)

    def save_request(self, did, credential, credential_info, is_restore=False):
        access_token = self.get_access_token(credential, credential_info)
        target_host, target_did = credential_info['targetHost'], credential_info['targetDID']
        req = self.get_request_by_did(did)
        if not req:
            self.insert_request(did, target_host, target_did, access_token, is_restore)
        else:
            self.update_request(did, target_host, target_did, access_token, req)

    def get_access_token(self, credential, credential_info):
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = \
            self.auth.backup_client_sign_in(target_host, credential, 'DIDBackupAuthResponse')
        return self.auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)

    def insert_request(self, did, target_host, target_did, access_token, is_restore=False):
        req = {
            USER_DID: did,
            BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE,
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_PROCESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, req, is_create=True)

    def update_request(self, did, target_host, target_did, access_token, req, is_restore=False):
        if request.args.get('is_multi') != 'True':
            # INFO: Use url parameter 'is_multi' to skip this check.
            cur_target_host = req.get(BACKUP_REQUEST_TARGET_HOST)
            cur_target_did = req.get(BACKUP_REQUEST_TARGET_DID)
            if cur_target_host and cur_target_did \
                    and (cur_target_host != target_host or cur_target_did != target_did):
                raise InvalidParameterException(msg='Do not support backup to multi hive node.')

        col_filter = {USER_DID: did, BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        update = {"$set": {
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_PROCESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }}
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, col_filter, update, is_extra=True)


class IpfsBackupServer:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting

    @hive_restful_response
    def promotion(self):
        pass

    @hive_restful_response
    def internal_backup(self):
        pass

    @hive_restful_response
    def internal_backup_state(self):
        pass

    @hive_restful_response
    def internal_restore(self):
        pass
