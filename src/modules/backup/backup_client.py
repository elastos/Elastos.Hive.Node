# -*- coding: utf-8 -*-

"""
The entrance for ipfs-backup module on the vault side.
"""
import json
import logging
import typing as t

from flask import g

from src.modules.backup.encryption import Encryption
from src.modules.files.ipfs_client import IpfsClient
from src.utils.consts import BACKUP_TARGET_TYPE, BACKUP_TARGET_TYPE_HIVE_NODE, BACKUP_REQUEST_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE, BACKUP_REQUEST_STATE, BACKUP_REQUEST_STATE_PROCESS, \
    BACKUP_REQUEST_STATE_MSG, BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_DID, BACKUP_REQUEST_TARGET_TOKEN, \
    BACKUP_REQUEST_STATE_STOP, BACKUP_REQUEST_STATE_SUCCESS, \
    URL_SERVER_INTERNAL_BACKUP, URL_SERVER_INTERNAL_RESTORE, \
    COL_IPFS_BACKUP_CLIENT, USR_DID, URL_V2
from src.utils.http_exception import BadRequestException, InsufficientStorageException
from src.modules.files.local_file import LocalFile
from src.utils.http_client import HttpClient
from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.subscription.vault import VaultManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.backup.backup_server_client import BackupServerClient
from src.modules.backup.backup_executor import BackupClientExecutor, RestoreExecutor


class BackupClient:
    """ Represents the backup client on the vault node side. """

    def __init__(self):
        self.auth = Auth()
        self.http = HttpClient()
        self.mcli = MongodbClient()
        self.user_manager = UserManager()
        self.vault_manager = VaultManager()
        self.ipfs_client = IpfsClient()

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
        BackupClientExecutor(g.usr_did, self, req, is_force=is_force).start()

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

        # if is_force, skip check.
        if not is_force:
            remote_action, remote_state, _, _ = client.get_state()

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

    def dump_database_data_to_backup_cids(self, user_did, encryption: Encryption, process_callback=t.Optional[t.Callable[[int, int], None]]):
        """ Each application holds its databases under the same user did.
        The steps to dump each database data to each application is under the specific user did and application did:

        - dump the specific database to a snapshot file;
        - upload this snapshot file into IPFS node
        """
        names = self.user_manager.get_database_names(user_did)
        metadata_list, length = list(), len(names)
        for i in range(length):
            if process_callback:
                process_callback(i + 1, length)

            d = {
                'path': LocalFile.generate_tmp_file_path(),
                'name': names[i]
            }
            # dump the database data to snapshot file.
            LocalFile.dump_mongodb_to_full_path(d['name'], d['path'])

            # encrypt the dump file.
            try:
                encrypt_path = encryption.encrypt_file(d['path'])
            except Exception as e:
                raise BadRequestException(f'Can not encrypt the dump file for the database {names[i]}: {e}')
            d['path'].unlink()

            # upload this snapshot file onto IPFS node.
            d['cid'] = self.ipfs_client.upload_file(encrypt_path)
            d['sha256'] = LocalFile.get_sha256(encrypt_path.as_posix())
            d['size'] = encrypt_path.stat().st_size
            encrypt_path.unlink()

            metadata_list.append(d)
        return metadata_list

    def send_root_backup_cid_to_backup_node(self, user_did, cid, sha256, size, is_force):
        """
        All vault data would be uploaded onto IPFS node and identified by CID.
        then this CID would be sent to backup node along with certain other meta information.
        """
        body = {'cid': cid,
                'sha256': sha256,
                'size': size,
                'is_force': is_force,
                'public_key': Encryption.get_service_did_public_key(False)}

        req = self.__get_request_doc(user_did)
        self.http.post(req[BACKUP_REQUEST_TARGET_HOST] + URL_V2 + URL_SERVER_INTERNAL_BACKUP,
                       req[BACKUP_REQUEST_TARGET_TOKEN], body, is_json=True, is_body=False, timeout=90)

    def get_request_metadata_from_backup_node(self, user_did):
        """
        When restoring vault data from a specific backup node, it will condcut the following steps:
        - get the root cid to recover vault data;
        - get a json document by the root cid, where the json document contains a list of CIDs
          to the files and database data on IPFS network.
        """
        req = self.__get_request_doc(user_did)
        data = self.http.get(req[BACKUP_REQUEST_TARGET_HOST] + URL_V2 + URL_SERVER_INTERNAL_RESTORE
                             + f'?public_key={Encryption.get_service_did_public_key(False)}',
                             req[BACKUP_REQUEST_TARGET_TOKEN])

        tmp_file = LocalFile.generate_tmp_file_path()
        self.ipfs_client.download_file(data['cid'], tmp_file, is_proxy=True, sha256=data['sha256'], size=data['size'])

        try:
            plain_path = Encryption.decrypt_file_with_curve25519(tmp_file, data['public_key'], False)
            tmp_file.unlink()
            with open(plain_path, 'r') as f:
                request_metadata = json.load(f)
        except Exception as e:
            raise BadRequestException('Failed to decrypt the metadata for restoring on the vault node.')

        if request_metadata['vault_size'] > self.vault_manager.get_vault(user_did).get_storage_quota():
            raise InsufficientStorageException('No enough space to restore, please upgrade the vault and try again.')
        return request_metadata

    def restore_database_by_dump_files(self, request_metadata):
        databases, secret_key, nonce = request_metadata['databases'], request_metadata['encryption']['secret_key'], request_metadata['encryption']['nonce']
        if not databases:
            logging.info('[BackupClient] No user databases dump files, skip.')
            return

        for d in databases:
            temp_file = LocalFile.generate_tmp_file_path()
            msg = self.ipfs_client.download_file(d['cid'], temp_file, is_proxy=True, sha256=d['sha256'], size=d['size'])
            if msg:
                logging.error(f'[BackupClient] Failed to download dump file for database {d["name"]}.')
                temp_file.unlink()
                raise BadRequestException(msg)

            plain_path = Encryption(secret_key, nonce).decrypt_file(temp_file)
            temp_file.unlink()

            LocalFile.restore_mongodb_from_full_path(plain_path)
            plain_path.unlink()
            logging.info(f'[BackupClient] Success to restore the dump file for database {d["name"]}.')

    def retry_backup_request(self):
        """ retry unfinished backup&restore action when node rebooted """

        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT)
        requests = col.find_many({})

        for req in requests:
            if req.get(BACKUP_REQUEST_STATE) != BACKUP_REQUEST_STATE_PROCESS:
                continue

            # only handle the state BACKUP_REQUEST_STATE_INPROGRESS

            user_did = req[USR_DID]
            logging.info(f"[BackupClient] Found unfinished request({user_did}), retry.")

            if req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_BACKUP:
                BackupClientExecutor(user_did, self, req, start_delay=30).start()
            elif req.get(BACKUP_REQUEST_ACTION) == BACKUP_REQUEST_ACTION_RESTORE:
                RestoreExecutor(user_did, self, start_delay=30).start()
            else:
                logging.error(f'[BackupClient] Unknown action({req.get(BACKUP_REQUEST_ACTION)}), skip.')
