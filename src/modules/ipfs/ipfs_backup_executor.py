# -*- coding: utf-8 -*-

import json
import logging
import threading
import traceback

from src.utils.consts import BACKUP_REQUEST_STATE_SUCCESS, BACKUP_REQUEST_STATE_FAILED
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
        size = temp_file.stat().st_size
        cid = fm.ipfs_upload_file_from_path(temp_file)
        temp_file.unlink()
        return cid, sha256, size

    @staticmethod
    def pin_cids_to_local_ipfs(request_metadata, is_only_file=False):
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
        database_cids = self.owner.dump_to_database_cids(self.did)
        file_cids = self.owner.get_file_cids_by_user_did(self.did)
        cid, sha256, size = self.get_request_metadata_cid(database_cids, file_cids)
        self.owner.send_request_metadata_to_server(self.did, cid, sha256, size)


class RestoreExecutor(ExecutorBase):
    def __init__(self, did, client):
        super().__init__(did, client, 'restore')

    def execute(self):
        request_metadata = self.owner.recv_request_metadata_from_server(self.did)
        self.__class__.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        self.owner.restore_database_by_dump_files(request_metadata)


class BackupServerExecutor(ExecutorBase):
    def __init__(self, did, server):
        super().__init__(did, server, 'backup_server')

    def execute(self):
        request_metadata = self.owner.get_request_metadata(self.did)
        self.__class__.pin_cids_to_local_ipfs(request_metadata)
