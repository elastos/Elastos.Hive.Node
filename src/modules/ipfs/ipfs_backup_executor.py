# -*- coding: utf-8 -*-

import json
import logging
import threading
import traceback
from datetime import datetime

from src.modules.ipfs.ipfs import IpfsFiles
from src.utils.consts import BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED, BACKUP_REQUEST_STATE, \
    BACKUP_REQUEST_STATE_PROCESS, BKSERVER_REQ_STATE
from src.utils.file_manager import fm
from src.utils.http_exception import HiveException
from src.utils_v1.common import gene_temp_file_name


class ExecutorBase(threading.Thread):
    def __init__(self, did, owner, action='backup'):
        super().__init__()
        self.did = did
        self.owner = owner
        self.action = action

    def run(self):
        try:
            logging.error('[ExecutorBase] Enter execute the executor.')
            self.execute()
            self.owner.update_request_state(self.did, BACKUP_REQUEST_STATE_SUCCESS)
            logging.error('[ExecutorBase] Leave execute the executor.')
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
                       'size': d['size']} for d in file_cids],
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
    def pin_cids_to_local_ipfs(request_metadata, is_only_file=False, is_file_pin_to_ipfs=True):
        if not request_metadata:
            logging.info('[ExecutorBase] Invalid request metadata, skip pin CIDs.')
            return

        ipfs_files = IpfsFiles()
        files = request_metadata.get('files')
        if files:
            for f in files:
                if is_file_pin_to_ipfs:
                    fm.ipfs_pin_cid(f['cid'])
                ipfs_files.increase_cid_ref(f['cid'], count=f['cid'])

        logging.info('[ExecutorBase] Success to pin all files CIDs.')

        if not is_only_file and request_metadata.get('databases'):
            for d in request_metadata.get('databases'):
                fm.ipfs_pin_cid(d['cid'])

        logging.info('[ExecutorBase] Success to pin all databases CIDs.')


class BackupExecutor(ExecutorBase):
    def __init__(self, did, client, req):
        super().__init__(did, client)
        self.req = req

    def execute(self):
        if self.req.get(BACKUP_REQUEST_STATE) != BACKUP_REQUEST_STATE_PROCESS:
            logging.info('[BackupExecutor] The state is not in processing, skip.')
            return
        database_cids = self.owner.dump_to_database_cids(self.did)
        logging.info('[BackupExecutor] Success to dump databases to CIDs.')
        total_file_size, file_cids = self.owner.get_file_cids_by_user_did(self.did)
        logging.info('[BackupExecutor] Success to get all file CIDs.')
        cid, sha256, size = self.get_request_metadata_cid(database_cids, file_cids, total_file_size)
        logging.info('[BackupExecutor] Success to get metadata CID')
        self.owner.send_request_metadata_to_server(self.did, cid, sha256, size)
        logging.info('[BackupExecutor] Success to send metadata CID to the backup node.')


class RestoreExecutor(ExecutorBase):
    def __init__(self, did, client):
        super().__init__(did, client, 'restore')

    def execute(self):
        request_metadata = self.owner.recv_request_metadata_from_server(self.did)
        logging.info('[RestoreExecutor] Success to get request metadata from the backup node.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        logging.info('[RestoreExecutor] Success to pin files CIDs.')
        self.owner.restore_database_by_dump_files(request_metadata)
        logging.info('[RestoreExecutor] Success to restore the dump files of the use\'s database.')


class BackupServerExecutor(ExecutorBase):
    def __init__(self, did, server, req):
        super().__init__(did, server, 'backup_server')
        self.req = req

    def execute(self):
        if self.req.get(BKSERVER_REQ_STATE) != BACKUP_REQUEST_STATE_PROCESS:
            logging.info('[BackupServerExecutor] The state is not in processing, skip.')
            return
        request_metadata = self.owner.get_server_request_metadata(self.did, self.req)
        logging.info('[BackupServerExecutor] Success to get request metadata.')
        self.__class__.pin_cids_to_local_ipfs(request_metadata)
        logging.info('[BackupServerExecutor] Success to get pin all CIDs.')
