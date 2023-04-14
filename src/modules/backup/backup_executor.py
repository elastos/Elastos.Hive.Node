# -*- coding: utf-8 -*-

import json
import logging
import threading
import time
import traceback
from datetime import datetime

from src.utils.consts import BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED, USR_DID, BACKUP_REQUEST_STATE_PROCESS, BACKUP_REQUEST_TARGET_HOST, \
    BACKUP_REQUEST_TARGET_TOKEN, BACKUP_REQUEST_ACTION_BACKUP, BACKUP_REQUEST_ACTION_RESTORE
from src.utils.http_exception import HiveException, BadRequestException
from src.modules.backup.backup_server_client import BackupServerClient
from src.modules.backup.encryption import Encryption
from src.modules.files.collection_file_metadata import CollectionFileMetadata
from src.modules.files.collection_ipfs_cid_ref import CollectionIpfsCidRef
from src.modules.database.mongodb_client import mcli
from src.modules.files.ipfs_client import IpfsClient
from src.modules.files.local_file import LocalFile


class ExecutorBase(threading.Thread):
    PROGRESS_DONE = '100'

    def __init__(self, user_did, owner, action, start_delay=0, is_force=False):
        super().__init__()
        self.user_did = user_did
        self.owner = owner  # BackupClient or BackupServer
        self.action = action
        self.start_delay = start_delay
        self.is_force = is_force

    def run(self):
        try:
            if self.start_delay > 0:
                time.sleep(self.start_delay)
            logging.info(f'[ExecutorBase] Enter execute the executor for {self.action}.')
            self.execute()
            self.update_progress(ExecutorBase.PROGRESS_DONE)
            logging.info(f'[ExecutorBase] Leave execute the executor for {self.action} without error.')
        except HiveException as e:
            msg = f'[ExecutorBase] Failed to {self.action}: {e.msg}'
            logging.error(msg)
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_FAILED, msg)
        except Exception as e:
            msg = f'[ExecutorBase] Unexpected failed to {self.action}: {traceback.format_exc()}'
            logging.error(msg)
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_FAILED, msg)

    def execute(self):
        # INFO: override this.
        pass

    def generate_root_backup_cid(self, database_cids, files_cids, total_file_size, encryption: Encryption):
        """ Create a json doc containing basic root informations:

        - database data DIDs;
        - files data DIDs;
        - total amount of vault data;
        - total amount of backup data to sync.
        - create timestamp.
        """

        secret_key, nonce = encryption.get_private_key()
        data = {
            'version': '1.0',
            'databases': [{'name': d['name'],
                           'sha256': d['sha256'],
                           'cid': d['cid'],
                           'size': d['size'],
                           'app_did': d['app_did']} for d in database_cids],
            'files': [{'sha256': d['sha256'],
                       'cid': d['cid'],
                       'size': d['size'],
                       'count': d['count']} for d in files_cids],
            USR_DID: self.user_did,
            "vault_size": mcli.get_col_vault().get_vault(self.user_did).get_storage_usage(),
            "backup_size": sum([d['size'] for d in database_cids]) + total_file_size,
            "create_time": datetime.now().timestamp(),
            "encryption": {
                "secret_key": secret_key,
                "nonce": nonce
            }
        }

        temp_file = LocalFile.generate_tmp_file_path()
        with temp_file.open('w') as f:
            json.dump(data, f)

        _, _, _, public_key = BackupServerClient.get_state_by_user_did(self.user_did)
        encryption_path = Encryption.encrypt_file_with_curve25519(temp_file, public_key, False)
        temp_file.unlink()

        sha256, size = LocalFile.get_sha256(encryption_path.as_posix()), encryption_path.stat().st_size
        cid = IpfsClient().upload_file(encryption_path)
        encryption_path.unlink()
        return cid, sha256, size, data

    @staticmethod
    def get_vault_usage_by_metadata(request_metadata):
        total_size = request_metadata['vault_size']
        files_size = sum([f['size'] for f in request_metadata['files']])
        return files_size, total_size - files_size

    @staticmethod
    def update_vault_usage_by_metadata(user_did, request_metadata):
        files_size, dbs_size = ExecutorBase.get_vault_usage_by_metadata(request_metadata)
        mcli.get_col_vault().update_vault_file_used_size(user_did, files_size, is_reset=True)
        mcli.get_col_vault().update_vault_database_used_size(user_did, files_size, is_reset=True)

    @staticmethod
    def handle_cids_in_local_ipfs(request_metadata,
                                  root_cid=None,
                                  contain_databases=True,
                                  contain_files=True,
                                  is_unpin=False,
                                  only_files_ref=False):
        """ Handle the CIDs of the backup metadata which defined in ipfs_backup_client.py

        default is pin&unpin all databases and files.

        :param request_metadata: The request json data of the backup processing.
        :param root_cid: Operate on root_cid if not None.
        :param contain_databases: Only operate files.
        :param contain_files: Whether it needs pin/unpin files to IPFS node, only for files of request_metadata
        :param is_unpin: Pin or unpin the file on the IPFS node.
        :param only_files_ref: Only increase & decrease the cid ref count of the files.
        """

        client = IpfsClient()

        def execute_pin_unpin(cid):
            client.cid_pin(cid) if not is_unpin else client.cid_unpin(cid)

        # pin or unpin the cid of request_metadata
        if root_cid:
            execute_pin_unpin(root_cid)
            logging.info('[ExecutorBase] Success to pin root cid.')

        # can not handle without request_metadata
        if not request_metadata:
            logging.info('[ExecutorBase] Invalid request metadata, skip pin CIDs.')
            return

        # pin or unpin database packages
        if contain_databases and request_metadata.get('databases'):
            for d in request_metadata.get('databases'):
                execute_pin_unpin(d['cid'])
            logging.info(f'[ExecutorBase] Success to {"pin" if not is_unpin else "unpin"} all databases CIDs.')

        # pin or unpin files
        if contain_files and request_metadata.get('files'):
            for f in request_metadata.get('files'):
                if not only_files_ref:
                    execute_pin_unpin(f['cid'])

                cid_ref = mcli.get_col(CollectionIpfsCidRef)
                if not is_unpin:
                    cid_ref.decrease_cid_ref(f['cid'], f['count'])
                else:
                    cid_ref.increase_cid_ref(f['cid'], f['count'])

            logging.info('[ExecutorBase] Success to pin all files CIDs.')

    def update_progress(self, progress):
        if progress != ExecutorBase.PROGRESS_DONE:
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_PROCESS, progress)
        else:
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_SUCCESS, '')

        self.owner.notify_progress(self.action, progress)


class BackupExecutor(ExecutorBase):
    def __init__(self, user_did, client, req, **kwargs):
        super().__init__(user_did, client, BACKUP_REQUEST_ACTION_BACKUP, **kwargs)
        self.req = req

    def execute(self):
        def callback_dump_databases(index, total):
            percent = str(int(15 * (index - 1) / total))
            self.update_progress(percent)

        encryption = Encryption()

        self.update_progress('0')

        database_cids = self.owner.dump_database_data_to_backup_cids(self.user_did, encryption, callback_dump_databases)
        self.update_progress('15')
        logging.info('[BackupExecutor] Dumped the database data to IPFS node and returned with array of CIDs')

        filedata_size, file_cids = CollectionFileMetadata.get_backup_file_metadatas(self.user_did)
        self.update_progress('25')
        logging.info('[BackupExecutor] Got an array of CIDs to file data')

        cid, sha256, size, request_metadata = self.generate_root_backup_cid(database_cids, file_cids, filedata_size, encryption)
        self.update_progress('35')
        logging.info(f'[BackupExecutor] Generated the root backup CID to vault data, request_metadata, {request_metadata}, cid, {cid}')

        self.owner.send_root_backup_cid_to_backup_node(self.user_did, cid, sha256, size, self.is_force)
        self.update_progress('50')
        logging.info('[BackupExecutor] Send the root backup CID to the backup node.')

        # wait until the server ends
        try:
            client = BackupServerClient(self.req[BACKUP_REQUEST_TARGET_HOST], token=self.req[BACKUP_REQUEST_TARGET_TOKEN])
            while True:
                remote_action, remote_state, remote_msg, _ = client.get_state()

                if remote_state == BACKUP_REQUEST_STATE_PROCESS:
                    self.update_progress(remote_msg)
                elif remote_state == BACKUP_REQUEST_STATE_SUCCESS:
                    break
                else:
                    raise BadRequestException(f'server error: {remote_msg}')

                time.sleep(2)
        except Exception as e:
            raise e
        finally:
            if 'http://localhost' not in self.req[BACKUP_REQUEST_TARGET_HOST]:  # for local dev
                # clean client side cids
                super().handle_cids_in_local_ipfs(request_metadata, root_cid=cid, contain_databases=True, contain_files=False, is_unpin=True)


class RestoreExecutor(ExecutorBase):
    def __init__(self, user_did, client, **kwargs):
        super().__init__(user_did, client, BACKUP_REQUEST_ACTION_RESTORE, **kwargs)

    def execute(self):
        self.update_progress('0')

        # only get the content
        request_metadata = self.owner.get_request_metadata_from_backup_node(self.user_did)
        self.update_progress('40')
        logging.info('[RestoreExecutor] Success to get request metadata from the backup node.')

        # direct download database packages and restore to mongodb
        self.owner.restore_database_by_dump_files(request_metadata)
        self.update_progress('60')
        logging.info("[RestoreExecutor] Success to restore the dump files of the user's database.")

        self.__class__.handle_cids_in_local_ipfs(request_metadata, contain_databases=False)
        self.update_progress('80')
        logging.info('[RestoreExecutor] Success to pin files CIDs.')

        self.__class__.update_vault_usage_by_metadata(self.user_did, request_metadata)
        logging.info('[RestoreExecutor] Success to update the usage of the vault.')


class BackupServerExecutor(ExecutorBase):
    def __init__(self, user_did, server, backup, **kwargs):
        super().__init__(user_did, server, 'backup_server', **kwargs)
        self.backup = backup

    def execute(self):
        self.update_progress('50')

        # request_metadata already pinned to ipfs node

        request_metadata = self.owner.get_server_request_metadata(self.user_did, self.backup)
        logging.info(f'[BackupServerExecutor] request_metadata: {request_metadata}')
        self.update_progress('60')
        logging.info('[BackupServerExecutor] Success to get request metadata.')

        self.__class__.handle_cids_in_local_ipfs(request_metadata)
        self.update_progress('80')
        logging.info('[BackupServerExecutor] Success to get pin all CIDs.')

        mcli.get_col_backup().update_backup_storage_used_size(self.user_did, request_metadata['backup_size'])
        logging.info('[BackupServerExecutor] Success to update storage size.')
