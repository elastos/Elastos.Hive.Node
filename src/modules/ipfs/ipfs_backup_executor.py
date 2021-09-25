# -*- coding: utf-8 -*-

import json
import logging
import threading
import time
import traceback
from datetime import datetime

from src.modules.ipfs.ipfs import IpfsFiles
from src.utils.consts import BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED
from src.utils.file_manager import fm
from src.utils.http_exception import HiveException
from src.utils_v1.common import gene_temp_file_name


class ExecutorBase(threading.Thread):
    def __init__(self, did, owner, **kwargs):
        super().__init__()
        self.did = did
        self.owner = owner
        self.action = kwargs.get('action', 'backup')
        self.start_delay = kwargs.get('start_delay', 0)
        self.is_force = kwargs.get('is_force', False)

    def run(self):
        try:
            if self.start_delay > 0:
                time.sleep(self.start_delay)
            logging.info(f'[ExecutorBase] Enter execute the executor for {self.action}.')
            self.execute()
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_SUCCESS)
            logging.info(f'[ExecutorBase] Leave execute the executor for {self.action}.')
        except HiveException as e:
            msg = f'[ExecutorBase] Failed to {self.action} on the vault side: {e}'
            logging.error(msg)
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_FAILED, msg)
        except Exception as e:
            msg = f'[ExecutorBase] Unexpected failed to {self.action} on the vault side: {traceback.format_exc()}'
            logging.error(msg)
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_FAILED, msg)

    def execute(self):
        # INFO: override this.
        pass

    def get_request_metadata_cid(self, database_cids, file_cids, total_file_size):
        data = {
            'databases': [{'name': d['name'],
                           'sha256': d['sha256'],
                           'cid': d['cid'],
                           'size': d['size']} for d in database_cids],
            'files': [{'sha256': d['sha256'],
                       'cid': d['cid'],
                       'size': d['size'],
                       'count': d['count']} for d in file_cids],
            'did': self.did,
            "vault_size": fm.get_vault_storage_size(self.did),
            "vault_package_size": sum([d['size'] for d in database_cids]) + total_file_size,
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
    def update_vault_usage_by_metadata(did, request_metadata):
        files_size, dbs_size = ExecutorBase.get_vault_usage_by_metadata(request_metadata)
        fm.update_vault_files_usage(did, files_size)
        fm.update_vault_dbs_usage(did, dbs_size)

    @staticmethod
    def pin_cids_to_local_ipfs(request_metadata,
                               is_only_file=False,
                               is_file_pin_to_ipfs=True,
                               root_cid=None,
                               is_unpin=False):
        execute_pin_unpin = fm.ipfs_pin_cid if not is_unpin else fm.ipfs_unpin_cid
        if root_cid:
            execute_pin_unpin(root_cid)
            logging.info('[ExecutorBase] Success to pin root cid.')

        if not request_metadata:
            logging.info('[ExecutorBase] Invalid request metadata, skip pin CIDs.')
            return

        ipfs_files = IpfsFiles()
        files = request_metadata.get('files')
        if files:
            for f in files:
                if is_file_pin_to_ipfs:
                    execute_pin_unpin(f['cid'])
                    if not is_unpin:
                        ipfs_files.increase_cid_ref(f['cid'], count=f['count'])
                    else:
                        ipfs_files.decrease_cid_ref(f['cid'], count=f['count'])
        logging.info('[ExecutorBase] Success to pin all files CIDs.')

        if not is_only_file and request_metadata.get('databases'):
            for d in request_metadata.get('databases'):
                execute_pin_unpin(d['cid'])
        logging.info('[ExecutorBase] Success to pin all databases CIDs.')


class BackupExecutor(ExecutorBase):
    def __init__(self, did, client, req, **kwargs):
        super().__init__(did, client, **kwargs)
        self.req = req

    def execute(self):
        database_cids = self.owner.dump_to_database_cids(self.did)
        logging.info('[BackupExecutor] Success to dump databases to CIDs.')
        total_file_size, file_cids = self.owner.get_file_cids_by_user_did(self.did)
        logging.info('[BackupExecutor] Success to get all file CIDs.')
        cid, sha256, size = self.get_request_metadata_cid(database_cids, file_cids, total_file_size)
        logging.info('[BackupExecutor] Success to get metadata CID')
        self.owner.send_request_metadata_to_server(self.did, cid, sha256, size, self.is_force)
        logging.info('[BackupExecutor] Success to send metadata CID to the backup node.')


class RestoreExecutor(ExecutorBase):
    def __init__(self, did, client, **kwargs):
        super().__init__(did, client, action='restore', **kwargs)

    def execute(self):
        request_metadata = self.owner.recv_request_metadata_from_server(self.did)
        logging.info('[RestoreExecutor] Success to get request metadata from the backup node.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        logging.info('[RestoreExecutor] Success to pin files CIDs.')
        self.owner.restore_database_by_dump_files(request_metadata)
        logging.info('[RestoreExecutor] Success to restore the dump files of the use\'s database.')
        self.__class__.update_vault_usage_by_metadata(self.did, request_metadata)
        logging.info('[RestoreExecutor] Success to update the usage of the vault.')


class BackupServerExecutor(ExecutorBase):
    def __init__(self, did, server, req, **kwargs):
        super().__init__(did, server, action='backup_server', **kwargs)
        self.req = req

    def execute(self):
        request_metadata = self.owner.get_server_request_metadata(self.did, self.req)
        logging.info('[BackupServerExecutor] Success to get request metadata.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata)
        logging.info('[BackupServerExecutor] Success to get pin all CIDs.')
        self.owner.update_storage_usage(self.did, request_metadata['vault_package_size'])
        logging.info('[BackupServerExecutor] Success to update storage size.')
