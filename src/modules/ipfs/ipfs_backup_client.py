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
import typing as t

from flask import g

from src.utils.consts import BACKUP_TARGET_TYPE, BACKUP_TARGET_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_PROCESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, \
    URL_SERVER_INTERNAL_BACKUP, URL_SERVER_INTERNAL_RESTORE, \
    COL_IPFS_BACKUP_CLIENT, USR_DID, URL_V2
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.did_mongo_db_resource import dump_mongodb_to_full_path, restore_mongodb_from_full_path
from src.utils.http_exception import BadRequestException, InsufficientStorageException
from src.utils.http_client import HttpClient
from src.utils.file_manager import fm
from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.ipfs.backup_server_client import BackupServerClient
from src.modules.ipfs.ipfs_backup_executor import BackupExecutor, RestoreExecutor
from src.modules.subscription.vault import VaultManager


class IpfsBackupClient:
    def __init__(self):
        self.auth = Auth()
        self.http = HttpClient()
        self.mcli = MongodbClient()
        self.user_manager = UserManager()
        self.vault_manager = VaultManager()

    def get_state(self):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        doc = self.__get_request_doc(g.usr_did)
        if not doc:
            # not do any backup or restore before
            return {
                'state': BACKUP_REQUEST_STATE_STOP,
                'result': BACKUP_REQUEST_STATE_SUCCESS,
                'message': '',
            }

        return {
            'state': doc[BACKUP_REQUEST_ACTION],
            'result': doc[BACKUP_REQUEST_STATE],
            'message': doc[BACKUP_REQUEST_STATE_MSG],
        }

    def backup(self, credential: str, is_force):
        """
        The client application request to backup vault data to target backup node.
         - Check a backup/restore proess already is inprogress; if not, then
         - Record the backup request in case to restart the backup/restore process
         - Create a dedeicated thread to:
            --- store all data on vault to local IPFS node to get the root CID;
            --- send this CID value to remote backup hive node;
            --- remote backup hive node will synchronize valut data from IPFS network to
                its local IPFS node via the root CID.

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did)

        credential_info = self.auth.get_backup_credential_info(g.usr_did, credential)
        client = self.__validate_remote_state(credential_info['targetHost'], credential, is_force, is_restore=False)
        req = self.__save_request_doc(g.usr_did, credential_info, client.get_token(), is_restore=False)
        BackupExecutor(g.usr_did, self, req, is_force=is_force).start()

    def restore(self, credential, is_force):
        """
        The client application request to store vault data from the backup node.
         - Check a backup/restore proess already is inprogress; if not, then
         - Record the backup request in case to restart the backup/restore process
         - Create a dedeicated thread to:
            --- Get a root CID from the backup node;
            --- Synhorize the vault data from local IPFS node (but currently from Gatway node)
                via root CID

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did)

        credential_info = self.auth.get_backup_credential_info(g.usr_did, credential)
        client = self.__validate_remote_state(credential_info['targetHost'], credential, is_force, is_restore=True)
        self.__save_request_doc(g.usr_did, credential_info, client.get_token(), is_restore=True)
        RestoreExecutor(g.usr_did, self).start()

    def __validate_remote_state(self, target_host, credential, is_force, is_restore):
        """ also do connectivity check """
        client = BackupServerClient(target_host, credential)
        remote_action, remote_state, _ = client.get_state()

        # if is_force, skip check.
        if not is_force:
            if is_restore and (remote_action != BACKUP_REQUEST_ACTION_BACKUP and remote_state != BACKUP_REQUEST_STATE_SUCCESS):
                raise BadRequestException('No latest successful backup data on the backup server.')

            # remote check: check first to make sure backup server can do backup & restore.
            if remote_state == BACKUP_REQUEST_STATE_PROCESS:
                raise BadRequestException('The backup server is in process.')

            # local check
            doc = self.__get_request_doc(g.usr_did)
            if doc and doc[BACKUP_REQUEST_STATE] == BACKUP_REQUEST_STATE_PROCESS:
                raise BadRequestException(f'Local "{doc[BACKUP_REQUEST_ACTION]}" is in process.')

        return client

    def __get_request_doc(self, user_did):
        filter_ = {USR_DID: user_did,
                   BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}
        return self.mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT).find_one(filter_)

    def __save_request_doc(self, user_did, credential_info, access_token, is_restore):
        target_host, target_did = credential_info['targetHost'], credential_info['targetDID']
        filter_ = {USR_DID: user_did,
                   BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}

        update = {'$set': {
            BACKUP_REQUEST_ACTION: BACKUP_REQUEST_ACTION_RESTORE if is_restore else BACKUP_REQUEST_ACTION_BACKUP,
            BACKUP_REQUEST_STATE: BACKUP_REQUEST_STATE_STOP,
            BACKUP_REQUEST_STATE_MSG: None,
            BACKUP_REQUEST_TARGET_HOST: target_host,
            BACKUP_REQUEST_TARGET_DID: target_did,
            BACKUP_REQUEST_TARGET_TOKEN: access_token}}

        self.mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT).update_one(filter_, update, upsert=True)
        return self.__get_request_doc(user_did)

    # the following is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        filter_ = {USR_DID: user_did,
                   BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}

        update = {'$set': {
            BACKUP_REQUEST_STATE: state,
            BACKUP_REQUEST_STATE_MSG: msg}}

        self.mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT).update_one(filter_, update)

    def dump_database_data_to_backup_cids(self, user_did, process_callback=t.Optional[t.Callable[[int, int], None]]):
        """
        Each application holds its database under same user did.
        The steps to dump each database data to each application under the specific did:
        - dump the specific database to a snapshot file;
        - upload this snapshot file into IPFS node
        """
        names = self.user_manager.get_database_names(user_did)
        metadata_list, length = list(), len(names)
        for i in range(length):
            if process_callback:
                process_callback(i + 1, length)

            d = {
                'path': gene_temp_file_name(),
                'name': names[i]
            }
            # dump the database data to snapshot file.
            dump_mongodb_to_full_path(d['name'], d['path'])

            # upload this snapshot file onto IPFS node.
            d['cid'] = fm.ipfs_upload_file_from_path(d['path'])
            d['sha256'] = fm.get_file_content_sha256(d['path'])
            d['size'] = d['path'].stat().st_size
            d['path'].unlink()

            metadata_list.append(d)
        return metadata_list

    def get_files_data_as_backup_cids(self, user_did):
        """
        All files data of the vault have been uploaded to IPFS node and save with array of cids.
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

        req = self.__get_request_doc(user_did)
        self.http.post(req[BACKUP_REQUEST_TARGET_HOST] + URL_V2 + URL_SERVER_INTERNAL_BACKUP,
                       req[BACKUP_REQUEST_TARGET_TOKEN], body, is_json=True, is_body=False, timeout=90)

    def get_vault_data_cid_from_backup_node(self, user_did):
        """
        When restoring vault data from a specific backup node, it will condcut the following steps:
        - get the root cid to recover vault data;
        - get a json document by the root cid, where the json document contains a list of CIDs
          to the files and database data on IPFS network.
        """
        req = self.__get_request_doc(user_did)
        data = self.http.get(req[BACKUP_REQUEST_TARGET_HOST] + URL_V2 + URL_SERVER_INTERNAL_RESTORE,
                             req[BACKUP_REQUEST_TARGET_TOKEN])
        request_metadata = fm.ipfs_download_file_content(data['cid'], is_proxy=True, sha256=data['sha256'], size=data['size'])

        if request_metadata['vault_size'] > fm.get_vault_max_size(user_did):
            raise InsufficientStorageException('No enough space to restore, please upgrade the vault and try again.')
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
                raise BadRequestException(msg)
            restore_mongodb_from_full_path(temp_file)
            temp_file.unlink()
            logging.info(f'[IpfsBackupClient] Success to restore the dump file for database {d["name"]}.')

    def retry_backup_request(self):
        """ retry unfinished backup&restore action when node rebooted """

        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT)
        requests = col.find_many({})

        for req in requests:
            if req.get(BACKUP_REQUEST_STATE) != BACKUP_REQUEST_STATE_PROCESS:
                continue

            # only handle the state BACKUP_REQUEST_STATE_INPROGRESS

            user_did = req[USR_DID]
            logging.info(f"[IpfsBackupClient] Found unfinished request({user_did}), retry.")

            if req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_BACKUP:
                BackupExecutor(user_did, self, req, start_delay=30).start()
            elif req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_RESTORE:
                RestoreExecutor(user_did, self, start_delay=30).start()
            else:
                logging.error(f'[IpfsBackupClient] Unknown action({req.get(BACKUP_REQUEST_ACTION)}), skip.')
