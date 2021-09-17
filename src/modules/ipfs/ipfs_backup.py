# -*- coding: utf-8 -*-

"""
The entrance for ipfs-backup module.

The definition of the request metadata:
{
    "databases": [{
        "name":
        "sha256":
        "cid":
        "size":
    }],
    "files": [{
        "sha256":
        "cid":
        "size":
    }],
    "user_did":
    "vault_size":
    "vault_package_size":
    "create_time":
}
"""
import json
import logging
import threading
import traceback

from flask import request

from src.modules.auth.auth import Auth
from src.utils.consts import BACKUP_REQUEST_TYPE, BACKUP_REQUEST_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_PROCESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.file_manager import fm
from src.utils.http_exception import InvalidParameterException, BadRequestException, HiveException
from src.utils.http_response import hive_restful_response
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.constants import VAULT_ACCESS_R, DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, USER_DID


class ExecutorBase(threading.Thread):
    def __init__(self, did, owner, action='backup'):
        super().__init__()
        self.did = did
        self.owner = owner
        self.action = action

    def run(self):
        try:
            self.execute()
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_SUCCESS)
        except HiveException as e:
            msg = f'Failed to {self.action} on the vault side: {e.get_error_response()}'
            logging.error(msg)
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_FAILED, msg)
        except Exception as e:
            msg = f'Unexpected failed to {self.action} on the vault side: {traceback.format_exc()}'
            logging.error(msg)
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_FAILED, msg)

    def execute(self):
        # INFO: override this.
        pass

    def get_request_metadata_cid(self, database_cids, file_cids):
        data = {
            'databases': [{'name': d['name'],
                           'sha256': d['sha256'],
                           'cid': d['cid'],
                           'size': d['size']} for d in database_cids],
            'files': [{'sha256': d['sha256'],
                       'cid': d['cid'],
                       'size': d['size']} for d in file_cids]
        }
        temp_file = gene_temp_file_name()
        with temp_file.open('w') as f:
            json.dump(data, f)
        sha256 = fm.get_file_content_sha256(temp_file)
        cid = fm.ipfs_upload_file_from_path(temp_file)
        temp_file.unlink()
        return cid, sha256

    def pin_cids_to_local_ipfs(self, request_metadata, is_only_file=False):
        if not request_metadata:
            return

        files = request_metadata.get('files')
        if files:
            for f in files:
                fm.ipfs_pin_cid(f['cid'])

        if not is_only_file and request_metadata.get('databases'):
            for d in request_metadata.get('databases'):
                fm.ipfs_pin_cid(d['cid'])


class BackupExecutor(ExecutorBase):
    def __init__(self, did, client):
        super().__init__(did, client)

    def execute(self):
        database_cids = self.owner.dump_to_database_cids()
        file_cids = self.owner.get_file_cids_by_user_did(self.did)
        cid, sha256 = self.get_request_metadata_cid(database_cids, file_cids)
        self.owner.send_request_metadata_to_server(cid, sha256)


class RestoreExecutor(ExecutorBase):
    def __init__(self, did, client):
        super().__init__(did, client, 'restore')

    def execute(self):
        request_metadata = self.owner.recv_request_metadata_from_server(self.did)
        self.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        self.owner.restore_database_by_dump_files(request_metadata)


class BackupServerExecutor(ExecutorBase):
    def __init__(self, did, server):
        super().__init__(did, server, 'backup_server')

    def execute(self):
        request_metadata = self.owner.get_request_metadata(self.did)
        self.pin_cids_to_local_ipfs(request_metadata)


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
        self.check_state_for_backup_or_restore(did)
        self.save_request(did, credential, credential_info)
        BackupExecutor(did, self).start()

    @hive_restful_response
    def restore(self, credential):
        did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.check_state_for_backup_or_restore(did)
        self.save_request(did, credential, credential_info, is_restore=True)
        RestoreExecutor(did, self).start()

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

    # the flowing is for the executors.

    def update_request_state(self, did, state, msg=None):
        col_filter = {USER_DID: did, BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        update = {"$set": {
            BACKUP_REQUEST_STATE: state,
            BACKUP_REQUEST_STATE_MSG: msg,
        }}
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, col_filter, update, is_extra=True)

    def dump_to_database_cids(self):
        databases = self._dump_databases()
        self._add_files_to_ipfs(databases)
        self._remove_database_dump_files(databases)
        return databases

    def get_file_cids_by_user_did(self, did):
        pass

    def send_request_metadata_to_server(self, cid, sha256):
        pass

    def recv_request_metadata_from_server(self, did):
        request_metadata = self._get_verified_request_metadata_from_server(did)
        self._check_can_be_restore(request_metadata)
        return request_metadata

    def restore_database_by_dump_files(self, request_metadata):
        pass

    def _dump_databases(self):
        pass

    def _add_files_to_ipfs(self, databases):
        pass

    def _remove_database_dump_files(self, databases):
        pass

    def _get_verified_request_metadata_from_server(self, did):
        pass

    def _check_can_be_restore(self, request_metadata):
        pass


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

    # the flowing is for the executors.

    def update_request_state(self, did, state, msg=None):
        pass

    def get_request_metadata(self, did):
        request_metadata = self._get_verified_request_metadata(did)
        self._check_can_be_backup(request_metadata)
        return request_metadata

    def _get_verified_request_metadata(self, did):
        pass

    def _check_can_be_backup(self, request_metadata):
        pass
