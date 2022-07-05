# -*- coding: utf-8 -*-

import json
import logging
import threading
import time
import traceback
from datetime import datetime

from src.modules.ipfs.ipfs_cid_ref import IpfsCidRef
from src.modules.subscription.vault import VaultManager
from src.utils.consts import BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED, USR_DID, BACKUP_REQUEST_STATE_PROCESS
from src.utils.file_manager import fm
from src.utils.http_exception import HiveException
from src.utils_v1.common import gene_temp_file_name


class ExecutorBase(threading.Thread):
    def __init__(self, user_did, owner, action, start_delay=0, is_force=False):
        super().__init__()
        self.user_did = user_did
        self.owner = owner
        self.action = action
        self.start_delay = start_delay
        self.is_force = is_force
        self.vault_manager = VaultManager()

    def run(self):
        try:
            if self.start_delay > 0:
                time.sleep(self.start_delay)
            logging.info(f'[ExecutorBase] Enter execute the executor for {self.action}.')
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_PROCESS)
            self.execute()
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_SUCCESS)
            logging.info(f'[ExecutorBase] Leave execute the executor for {self.action} without error.')
        except HiveException as e:
            msg = f'[ExecutorBase] Failed to {self.action} on the vault side: {e.msg}'
            logging.error(msg)
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_FAILED, msg)
        except Exception as e:
            msg = f'[ExecutorBase] Unexpected failed to {self.action} on the vault side: {traceback.format_exc()}'
            logging.error(msg)
            self.owner.update_request_state(self.user_did, BACKUP_REQUEST_STATE_FAILED, msg)

    def execute(self):
        # INFO: override this.
        pass

    def generate_root_backup_cid(self, database_cids, files_cids, total_file_size):
        """
        Create a json doc containing basic root informations:
        - database data DIDs;
        - files data DIDs;
        - total amount of vault data;
        - total amount of backup data to sync.
        - create timestamp.
        """

        data = {
            'databases': [{'name': d['name'],
                           'sha256': d['sha256'],
                           'cid': d['cid'],
                           'size': d['size']} for d in database_cids],
            'files': [{'sha256': d['sha256'],
                       'cid': d['cid'],
                       'size': d['size'],
                       'count': d['count']} for d in files_cids],
            USR_DID: self.user_did,
            "vault_size": self.vault_manager.get_vault(self.user_did).get_storage_usage(),
            "backup_size": sum([d['size'] for d in database_cids]) + total_file_size,
            "create_time": datetime.now().timestamp(),
        }

        temp_file = gene_temp_file_name()
        with temp_file.open('w') as f:
            json.dump(data, f)

        sha256 = fm.get_file_content_sha256(temp_file)
        size = temp_file.stat().st_size
        cid = fm.ipfs_upload_file_from_path(temp_file)
        temp_file.unlink()
        return cid, sha256, size

    @staticmethod
    def get_vault_usage_by_metadata(request_metadata):
        total_size = request_metadata['vault_size']
        files_size = sum([f['size'] for f in request_metadata['files']])
        return files_size, total_size - files_size

    @staticmethod
    def update_vault_usage_by_metadata(user_did, request_metadata):
        files_size, dbs_size = ExecutorBase.get_vault_usage_by_metadata(request_metadata)
        vault_manager = VaultManager()
        vault_manager.update_user_files_size(user_did, files_size, is_reset=True)
        vault_manager.update_user_databases_size(user_did, files_size, is_reset=True)

    @staticmethod
    def pin_cids_to_local_ipfs(request_metadata,
                               is_only_file=False,
                               is_file_pin_to_ipfs=True,
                               root_cid=None,
                               is_unpin=False):
        """
        Handle the CIDs of the backup metadata which defined in ipfs_backup_client.py

        :param request_metadata: The request json data of the backup processing.
        :param is_only_file: Only operate the CIDs of the files. Or to handle database packages.
        :param is_file_pin_to_ipfs: Whether it needs pin/unpin files to IPFS node, only for files of request_metadata
        :param root_cid: The CID for the request metadata file.
        :param is_unpin: Pin or unpin the file on the IPFS node.
        """

        execute_pin_unpin = fm.ipfs_pin_cid if not is_unpin else fm.ipfs_unpin_cid

        # pin or unpin the cid of request_metadata
        if root_cid:
            execute_pin_unpin(root_cid)
            logging.info('[ExecutorBase] Success to pin root cid.')

        # can not handle without request_metadata
        if not request_metadata:
            logging.info('[ExecutorBase] Invalid request metadata, skip pin CIDs.')
            return

        # pin or unpin files
        if is_file_pin_to_ipfs and request_metadata.get('files'):
            for f in request_metadata.get('files'):
                execute_pin_unpin(f['cid'])
                cid_ref = IpfsCidRef(f['cid'])
                if not is_unpin:
                    cid_ref.decrease(f['count'])
                else:
                    cid_ref.increase(f['count'])
            logging.info('[ExecutorBase] Success to pin all files CIDs.')

        # pin or unpin database packages
        if not is_only_file and request_metadata.get('databases'):
            for d in request_metadata.get('databases'):
                execute_pin_unpin(d['cid'])
            logging.info(f'[ExecutorBase] Success to {"pin" if not is_unpin else "unpin"} all databases CIDs.')


class BackupExecutor(ExecutorBase):
    def __init__(self, user_did, client, req, **kwargs):
        super().__init__(user_did, client, 'backup', **kwargs)
        self.req = req

    def execute(self):
        database_cids = self.owner.dump_database_data_to_backup_cids(self.user_did)
        logging.info('[BackupExecutor] Dumped the database data to IPFS node and returned with array of CIDs')
        filedata_size, file_cids = self.owner.get_files_data_as_backup_cids(self.user_did)
        logging.info('[BackupExecutor] Got an array of CIDs to file data')
        cid, sha256, size = self.generate_root_backup_cid(database_cids, file_cids, filedata_size)
        logging.info('[BackupExecutor] Generated the root backup CID to vault data.')
        self.owner.send_root_backup_cid_to_backup_node(self.user_did, cid, sha256, size, self.is_force)
        logging.info('[BackupExecutor] Send the root backup CID to the backup node.')


class RestoreExecutor(ExecutorBase):
    def __init__(self, user_did, client, **kwargs):
        super().__init__(user_did, client, 'restore', **kwargs)

    def execute(self):
        request_metadata = self.owner.get_vault_data_cid_from_backup_node(self.user_did)
        logging.info('[RestoreExecutor] Success to get request metadata from the backup node.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        logging.info('[RestoreExecutor] Success to pin files CIDs.')
        self.owner.restore_database_by_dump_files(request_metadata)
        logging.info("[RestoreExecutor] Success to restore the dump files of the user's database.")
        self.__class__.update_vault_usage_by_metadata(self.user_did, request_metadata)
        logging.info('[RestoreExecutor] Success to update the usage of the vault.')


class BackupServerExecutor(ExecutorBase):
    def __init__(self, user_did, server, req, **kwargs):
        super().__init__(user_did, server, 'backup_server', **kwargs)
        self.req = req

    def execute(self):
        request_metadata = self.owner.get_server_request_metadata(self.user_did, self.req)
        logging.info('[BackupServerExecutor] Success to get request metadata.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata)
        logging.info('[BackupServerExecutor] Success to get pin all CIDs.')
        self.owner.update_storage_usage(self.user_did, request_metadata['backup_size'])
        logging.info('[BackupServerExecutor] Success to update storage size.')
