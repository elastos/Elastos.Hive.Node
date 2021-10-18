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
        "count":
    }],
    "user_did":
    "vault_size":
    "vault_package_size":
    "create_time":
}
"""
import logging

from flask import request

from src.modules.auth.auth import Auth
from src.modules.ipfs.ipfs_backup_executor import BackupExecutor, RestoreExecutor
from src.utils.consts import BACKUP_REQUEST_TYPE, BACKUP_REQUEST_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_INPROGRESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, \
    URL_IPFS_BACKUP_SERVER_BACKUP, URL_IPFS_BACKUP_SERVER_RESTORE, URL_IPFS_BACKUP_SERVER_BACKUP_STATE, \
    COL_IPFS_BACKUP_CLIENT, USR_DID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.file_manager import fm
from src.utils.http_client import HttpClient
from src.utils.http_exception import InvalidParameterException, BadRequestException, \
    InsufficientStorageException
from src.utils.http_response import hive_restful_response
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.constants import VAULT_ACCESS_R, DID_INFO_DB_NAME
from src.utils_v1.did_mongo_db_resource import export_mongo_db_to_full_path, import_mongo_db_by_full_path


class IpfsBackupClient:
    def __init__(self):
        self.auth = Auth()
        self.http = HttpClient()

    @hive_restful_response
    def get_state(self):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        return self.get_state_from_request(user_did)

    @hive_restful_response
    def backup(self, credential, is_force):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info  = self.auth.get_backup_credential_info(credential)
        if not is_force:
            self.check_backup_restore_in_progress(user_did)
        req = self.save_request(user_did, credential, credential_info)
        BackupExecutor(user_did, self, req, is_force=is_force).start()

    @hive_restful_response
    def restore(self, credential, is_force):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        if not is_force:
            self.check_backup_restore_in_progress(user_did)
        self.save_request(user_did, credential, credential_info, is_restore=True)
        RestoreExecutor(user_did, self).start()

    def check_backup_restore_in_progress(self, user_did):
        result = self.get_state_from_request(user_did)
        if result['result'] == BACKUP_REQUEST_STATE_INPROGRESS:
            raise BadRequestException(msg=f'The backup/restore is being in progress. Please await for this process finished')

    def get_state_from_request(self, user_did):
        state, result, msg = BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, ''
        req = self.get_request_by_did(user_did)
        if req:
            state  = req.get(BACKUP_REQUEST_ACTION)
            result = req.get(BACKUP_REQUEST_STATE)
            msg    = req.get(BACKUP_REQUEST_STATE_MSG)

            ## request to remote backup node to retrieve the current backup progress state if
            ## its being backuped.
            if state == BACKUP_REQUEST_ACTION_BACKUP and result == BACKUP_REQUEST_STATE_SUCCESS:
                body = self.http.get(req.get(BACKUP_REQUEST_TARGET_HOST) + URL_IPFS_BACKUP_SERVER_BACKUP_STATE,
                                     req.get(BACKUP_REQUEST_TARGET_TOKEN))
                result, msg = body['result'], body['message']
        return {
            'state': state if state else BACKUP_REQUEST_STATE_STOP,
            'result': result if result else BACKUP_REQUEST_STATE_SUCCESS,
            'message': msg if msg else '',
        }

    def get_request_by_did(self, user_did):
        col_filter = {USR_DID: user_did,
                      BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        return cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, col_filter,
                                   create_on_absence=True, throw_exception=False)

    def save_request(self, user_did, credential, credential_info, is_restore=False):
        access_token = self.get_access_token(credential, credential_info)
        target_host, target_did = credential_info['targetHost'], credential_info['targetDID']
        req = self.get_request_by_did(user_did)
        if not req:
            self.insert_request(user_did, target_host, target_did, access_token, is_restore=is_restore)
        else:
            self.update_request(user_did, target_host, target_did, access_token, req, is_restore=is_restore)
        return self.get_request_by_did(user_did)

    def get_access_token(self, credential, credential_info):
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = \
            self.auth.backup_client_sign_in(target_host, credential, 'DIDBackupAuthResponse')
        return self.auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)

    def insert_request(self, user_did, target_host, target_did, access_token, is_restore=False):
        new_doc = {
            USR_DID: user_did,
            BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE,
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_INPROGRESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }
        cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, new_doc, is_create=True)

    def update_request(self, user_did, target_host, target_did, access_token, req, is_restore=False):
        if request.args.get('is_multi') != 'True':
            # INFO: Use url parameter 'is_multi' to skip this check.
            cur_target_host = req.get(BACKUP_REQUEST_TARGET_HOST)
            cur_target_did = req.get(BACKUP_REQUEST_TARGET_DID)
            if cur_target_host and cur_target_did \
                    and (cur_target_host != target_host or cur_target_did != target_did):
                raise InvalidParameterException(msg='Do not support backup to multi hive node.')

        updated_doc = {
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_INPROGRESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }

        _filter = {USR_DID: user_did,
                      BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, _filter, {'$set': updated_doc}, is_extra=True)

    # the flowing is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        updated_doc = {
            BACKUP_REQUEST_STATE: state,
            BACKUP_REQUEST_STATE_MSG: msg
        }

        _filter = {USR_DID: user_did, BACKUP_REQUEST_TYPE: BACKUP_REQUEST_TYPE_HIVE_NODE}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, _filter, {'$set': updated_doc}, is_extra=True)

    def dump_to_database_cids(self, user_did):
        db_names = cli.get_all_user_database_names(user_did)
        databases = list()
        for db_name in db_names:
            d = {
                'path': gene_temp_file_name(),
                'name': db_name
            }
            is_success = export_mongo_db_to_full_path(d['name'], d['path'])
            if not is_success:
                raise BadRequestException(f'Failed to dump {d["name"]} for {user_did}')
            d['sha256'] = fm.get_file_content_sha256(d['path'])
            d['size'] = d['path'].stat().st_size
            d['cid'] = fm.ipfs_upload_file_from_path(d['path'])
            d['path'].unlink()
            databases.append(d)
        return databases

    def get_file_cids_by_user_did(self, user_did):
        return fm.get_file_cid_metadatas(user_did)

    def send_request_metadata_to_server(self, user_did, cid, sha256, size, is_force):
        req = self.get_request_by_did(user_did)
        body = {'cid': cid, 'sha256': sha256, 'size': size, 'is_force': is_force}
        self.http.post(req[BACKUP_REQUEST_TARGET_HOST] + URL_IPFS_BACKUP_SERVER_BACKUP,
                       req[BACKUP_REQUEST_TARGET_TOKEN], body, is_json=True, is_body=False)

    def recv_request_metadata_from_server(self, user_did):
        request_metadata = self._get_verified_request_metadata_from_server(user_did)
        self.check_can_be_restore(user_did, request_metadata)
        return request_metadata

    def restore_database_by_dump_files(self, request_metadata):
        databases = request_metadata['databases']
        if not databases:
            logging.info('[IpfsBackupClient] No user databases dump files, skip.')
            return
        for d in databases:
            temp_file = gene_temp_file_name()
            msg = fm.ipfs_download_file_to_path(d['cid'], temp_file, is_proxy=True, sha256=d['sha256'], size=d['size'])
            if msg:
                logging.error(f'[IpfsBackupClient] Failed to download dump file for database {d["name"]}.')
                temp_file.unlink()
                raise BadRequestException(msg=msg)
            import_mongo_db_by_full_path(temp_file)
            temp_file.unlink()
            logging.info(f'[IpfsBackupClient] Success to restore the dump file for database {d["name"]}.')

    def _get_verified_request_metadata_from_server(self, user_did):
        req = self.get_request_by_did(user_did)
        body = self.http.get(req[BACKUP_REQUEST_TARGET_HOST] + URL_IPFS_BACKUP_SERVER_RESTORE,
                             req[BACKUP_REQUEST_TARGET_TOKEN])
        return fm.ipfs_download_file_content(body['cid'], is_proxy=True, sha256=body['sha256'], size=body['size'])

    def check_can_be_restore(self, user_did, request_metadata):
        if request_metadata['vault_size'] > fm.get_vault_max_size(user_did):
            raise InsufficientStorageException(msg='No enough space for restore.')

    def retry_backup_request(self, user_did):
        req = self.get_request_by_did(user_did)
        if not req or req.get(BACKUP_REQUEST_STATE) != BACKUP_REQUEST_STATE_INPROGRESS:
            return
        elif req.get(BACKUP_REQUEST_STATE) != BACKUP_REQUEST_STATE_INPROGRESS:
            return
        logging.info(f"[IpfsBackupClient] Found uncompleted request({req.get(USR_DID)}), retry.")
        if req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_BACKUP:
            BackupExecutor(user_did, self, req, start_delay=30).start()
        elif req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_RESTORE:
            RestoreExecutor(user_did, self, start_delay=30).start()
        else:
            logging.error(f'[IpfsBackupClient] Unknown action({req.get(BACKUP_REQUEST_ACTION)}), skip.')
