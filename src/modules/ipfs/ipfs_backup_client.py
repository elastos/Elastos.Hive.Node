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
from src.utils.consts import BACKUP_TARGET_TYPE, BACKUP_TARGET_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_INPROGRESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, \
    URL_VAULT_BACKUP_SERVICE_BACKUP, URL_VAULT_BACKUP_SERVICE_RESTORE, URL_VAULT_BACKUP_SERVICE_STATE, \
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
        return self.get_remote_backup_state(user_did);

    @hive_restful_response
    def backup(self, credential, is_force):
        """
        The client application request to backup vault data to target backup node.
         - Check a backup/restore proess already is inprogress; if not, then
         - Record the backup request in case to restart the backup/restore process
         - Create a dedeicated thread to:
            --- store all data on vault to local IPFS node to get the root CID;
            --- send this CID value to remote backup hive node;
            --- remote backup hive node will synchronize valut data from IPFS network to
                its local IPFS node via the root CID.
        """
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        if not is_force:
            self.check_remote_backup_in_progress(user_did)
        req = self.save_request(user_did, credential, credential_info)
        BackupExecutor(user_did, self, req, is_force=is_force).start()

    @hive_restful_response
    def restore(self, credential, is_force):
        """
        The client application request to store vault data from the backup node.
         - Check a backup/restore proess already is inprogress; if not, then
         - Record the backup request in case to restart the backup/restore process
         - Create a dedeicated thread to:
            --- Get a root CID from the backup node;
            --- Synhorize the vault data from local IPFS node (but currently from Gatway node)
                via root CID
        """
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        if not is_force:
            self.check_remote_backup_in_progress(user_did)
        self.save_request(user_did, credential, credential_info, is_restore=True)
        RestoreExecutor(user_did, self).start()

    def check_remote_backup_in_progress(self, user_did):
        result = self.get_remote_backup_state(user_did)
        if result['result'] == BACKUP_REQUEST_STATE_INPROGRESS:
            raise BadRequestException(msg=f'The remote backup is being in progress. Please await the process finished')

    def get_remote_backup_state(self, user_did):
        state, result, msg = BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, ''
        req = self.get_request(user_did)
        if req:
            state = req.get(BACKUP_REQUEST_ACTION)
            result = req.get(BACKUP_REQUEST_STATE)
            msg = req.get(BACKUP_REQUEST_STATE_MSG)

            # request to remote backup node to retrieve the current backup progress state if
            # its being backuped.
            if state == BACKUP_REQUEST_ACTION_BACKUP and result == BACKUP_REQUEST_STATE_SUCCESS:
                body = self.http.get(req.get(BACKUP_REQUEST_TARGET_HOST) + URL_VAULT_BACKUP_SERVICE_STATE,
                                     req.get(BACKUP_REQUEST_TARGET_TOKEN))
                result, msg = body['result'], body['message']
        return {
            'state': state if state else BACKUP_REQUEST_STATE_STOP,
            'result': result if result else BACKUP_REQUEST_STATE_SUCCESS,
            'message': msg if msg else '',
        }

    def get_request(self, user_did):
        col_filter = {USR_DID: user_did,
                      BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}
        return cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, col_filter,
                                   create_on_absence=True,
                                   throw_exception=False)

    def save_request(self, user_did, credential, credential_info, is_restore=False):
        # verify the credential
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = \
            self.auth.backup_client_sign_in(target_host, credential, 'DIDBackupAuthResponse')

        access_token =  self.auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)
        target_host, target_did = credential_info['targetHost'], credential_info['targetDID']
        req = self.get_request(user_did)
        if not req:
            self.insert_request(user_did, target_host, target_did, access_token, is_restore=is_restore)
        else:
            self.update_request(user_did, target_host, target_did, access_token, req, is_restore=is_restore)
        return self.get_request(user_did)

    def insert_request(self, user_did, target_host, target_did, access_token, is_restore=False):
        new_doc = {
            USR_DID: user_did,
            BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE,
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_INPROGRESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }
        cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, new_doc, create_on_absence=True)

    def update_request(self, user_did, target_host, target_did, access_token, req, is_restore=False):
        # if request.args.get('is_multi') != 'True':
        #     # INFO: Use url parameter 'is_multi' to skip this check.
        #     cur_target_host = req.get(BACKUP_REQUEST_TARGET_HOST)
        #     cur_target_did = req.get(BACKUP_REQUEST_TARGET_DID)
        #     if cur_target_host and cur_target_did \
        #             and (cur_target_host != target_host or cur_target_did != target_did):
        #         raise InvalidParameterException(msg='Do not support backup to multi hive node.')

        updated_doc = {
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_INPROGRESS,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token
        }

        _filter = {USR_DID: user_did,
                   BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, _filter, {'$set': updated_doc}, is_extra=True)

    # the flowing is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        updated_doc = {
            BACKUP_REQUEST_STATE: state,
            BACKUP_REQUEST_STATE_MSG: msg
        }

        _filter = {USR_DID: user_did, BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_CLIENT, _filter, {'$set': updated_doc}, is_extra=True)

    def dump_database_data_to_backup_cids(self, user_did):
        """
        Each application holds its database under same user did.
        The steps to dump each database data to each application under the specific did:
        - dump the specific database to a snapshot file;
        - upload this snapshot file into IPFS node
        """
        names = cli.get_all_user_database_names(user_did)
        metadata_list = list()
        for name in names:
            d = {
                'path': gene_temp_file_name(),
                'name': name
            }
            ## dump the database data to snapshot file.
            succeeded = export_mongo_db_to_full_path(d['name'], d['path'])
            if not succeeded:
                raise BadRequestException(f'Failed to dump {d["name"]} for {user_did}')

            ## upload this snapshot file onto IPFS node.
            d['cid'] = fm.ipfs_upload_file_from_path(d['path'])
            d['sha256'] = fm.get_file_content_sha256(d['path'])
            d['size'] = d['path'].stat().st_size
            d['path'].unlink()

            metadata_list.append(d)
        return metadata_list

    def get_files_data_as_backup_cids(self, user_did):
        """
        All files data have been uploaded to IPFS node and save with array of cids.
        The method here is to get array of cids to save it as json document then.
        """
        return fm.get_file_cid_metadatas(user_did)

    def send_root_backup_cid_to_backup_node(self, user_did, cid, sha256, size, is_force):
        """
        All vault data would be uploaded onto IPFS node and identified by CID.
        then this CID would be sent to backup node along with certain other meta information.
        """
        body = {'cid': cid,
                'sha256': sha256,
                'size': size,
                'is_force': is_force}

        req = self.get_request(user_did)
        self.http.post(req[BACKUP_REQUEST_TARGET_HOST] + URL_VAULT_BACKUP_SERVICE_BACKUP,
                       req[BACKUP_REQUEST_TARGET_TOKEN], body, is_json=True, is_body=False)

    def get_vault_data_cid_from_backup_node(self, user_did):
        """
        When restoring vault data from a specific backup node, it will condcut the following steps:
        - get the root cid to recover vault data;
        - get a json document by the root cid, where the json document contains a list of CIDs
          to the files and database data on IPFS network.
        """
        req = self.get_request(user_did)
        data = self.http.get(req[BACKUP_REQUEST_TARGET_HOST] + URL_VAULT_BACKUP_SERVICE_RESTORE,
                             req[BACKUP_REQUEST_TARGET_TOKEN])
        vault_metadata = fm.ipfs_download_file_content(data['cid'], is_proxy=True, sha256=data['sha256'], size=data['size'])

        if vault_metadata['vault_size'] > fm.get_vault_max_size(user_did):
            raise InsufficientStorageException(msg='No alowed enough space to restore vault data from backup node.')
        return vault_metadata

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

    def retry_backup_request(self, user_did):
        req = self.get_request(user_did)
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
