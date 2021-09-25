# -*- coding: utf-8 -*-
import _thread
import logging
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path

from flask import request

from src.utils_v1.common import get_file_checksum_list, gene_temp_file_name, \
    create_full_path_dir
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, VAULT_BACKUP_INFO_STATE, USER_DID, \
    VAULT_BACKUP_INFO_TIME, VAULT_BACKUP_INFO_TYPE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, VAULT_BACKUP_INFO_MSG, \
    VAULT_BACKUP_INFO_DRIVE, VAULT_BACKUP_INFO_TOKEN, VAULT_BACKUP_SERVICE_MAX_STORAGE, APP_ID, CHUNK_SIZE, \
    VAULT_BACKUP_SERVICE_COL, VAULT_BACKUP_SERVICE_DID, VAULT_BACKUP_SERVICE_USE_STORAGE, \
    VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, VAULT_BACKUP_SERVICE_MODIFY_TIME, \
    VAULT_BACKUP_SERVICE_STATE, VAULT_BACKUP_SERVICE_USING
from src.utils_v1.did_file_info import get_vault_path, get_dir_size
from src.utils_v1.did_mongo_db_resource import get_save_mongo_db_path
from src.utils_v1.payment.payment_config import PaymentConfig
from src.utils_v1.payment.vault_backup_service_manage import get_vault_backup_path
from src.utils_v1.payment.vault_service_manage import VAULT_SERVICE_STATE_RUNNING
from src.utils_v1.vault_backup_info import VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS, \
    VAULT_BACKUP_MSG_FAILED
from src.modules.auth.auth import Auth
from src.utils.db_client import cli
from src.utils.did_auth import check_auth2
from src.utils.http_client import HttpClient, HttpServer
from src.utils.http_exception import BackupIsInProcessingException, InsufficientStorageException, \
    InvalidParameterException, BadRequestException, AlreadyExistsException, BackupNotFoundException, \
    NotImplementedException
from src.utils.consts import URL_BACKUP_SERVICE, URL_BACKUP_FINISH, URL_BACKUP_FILES, URL_BACKUP_FILE, \
    URL_BACKUP_PATCH_HASH, URL_BACKUP_PATCH_FILE, URL_RESTORE_FINISH, URL_BACKUP_PATCH_DELTA, URL_IPFS_BACKUP_PIN_CIDS, \
    BACKUP_FILE_SUFFIX, URL_IPFS_BACKUP_GET_DBFILES, STATE, STATE_RUNNING, STATE_FINISH, URL_IPFS_BACKUP_STATE, DID, \
    ORIGINAL_SIZE
from src.utils.file_manager import fm
from src.utils.http_response import hive_restful_response, hive_stream_response
from src.utils_v1.auth import get_current_node_did_string


def clog():
    return logging.getLogger('BACKUP_CLIENT')


def slog():
    return logging.getLogger('BACKUP_SERVER')


class BackupClient:
    def __init__(self, app=None, hive_setting=None, is_ipfs=False):
        self.http = HttpClient()
        self.backup_thread = None
        self.hive_setting = hive_setting
        self.mongo_host, self.mongo_port = None, None
        if hive_setting:
            self.mongo_host, self.mongo_port = self.hive_setting.MONGO_HOST, self.hive_setting.MONGO_PORT
        self.auth = Auth(app, hive_setting)
        self.is_ipfs = is_ipfs

    def check_backup_status(self, did, is_restore=False):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {USER_DID: did}, is_create=True)
        if doc and doc[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP \
                and doc[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
            raise BackupIsInProcessingException('The backup/restore is in process.')

        if is_restore and not (doc[VAULT_BACKUP_INFO_STATE] == VAULT_BACKUP_STATE_STOP
                               or doc[VAULT_BACKUP_INFO_MSG] == VAULT_BACKUP_MSG_SUCCESS):
            raise BadRequestException(msg='No successfully backup for restore.')

    def get_access_token(self, credential, credential_info):
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = \
            self.auth.backup_client_sign_in(target_host, credential, 'DIDBackupAuthResponse')
        return self.auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)

    def execute_backup(self, did, credential_info, access_token):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {USER_DID: did},
                              {"$set": {USER_DID: did,
                                        VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
                                        VAULT_BACKUP_INFO_TYPE: VAULT_BACKUP_INFO_TYPE_HIVE_NODE,
                                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp(),
                                        VAULT_BACKUP_INFO_DRIVE: credential_info['targetHost'],
                                        VAULT_BACKUP_INFO_TOKEN: access_token}},
                              options={'upsert': True}, is_create=True)

        clog().debug('start new thread for backup processing.')

        if self.hive_setting.BACKUP_IS_SYNC:
            self.__class__.backup_main(did, self)
        else:
            _thread.start_new_thread(self.__class__.backup_main, (did, self))

    def update_backup_state(self, did, state, msg):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {USER_DID: did},
                              {"$set": {VAULT_BACKUP_INFO_STATE: state,
                                        VAULT_BACKUP_INFO_MSG: msg,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp()}})

    @staticmethod
    def backup_main(did, client):
        try:
            clog().info(f'[backup_main] enter backup thread, {did}, {client}.')
            client.backup(did)
        except Exception as e:
            clog().error(f'Failed to backup really: {traceback.format_exc()}')
            client.delete_mongodb_data(did)
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)
        clog().info('[backup_main] leave backup thread.')

    @staticmethod
    def restore_main(did, client):
        try:
            clog().info(f'[restore_main] enter restore thread, {did}, {client}.')
            client.restore(did)
        except Exception as e:
            clog().error(f'[restore_main] Failed to restore really: {traceback.format_exc()}')
            client.delete_mongodb_data(did)
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)

    def backup(self, did):
        clog().info('[backup_main] enter backup().')
        cli.export_mongodb(did)
        clog().info('[backup_main] success to export mongodb data.')

        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {USER_DID: did})
        clog().info('[backup_main] success to get backup info.')
        if self.is_ipfs:
            vault_size = fm.get_vault_storage_size(did)
            self.update_server_state_to(
                doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN], STATE_RUNNING, vault_size)
            clog().info('[backup_main: ipfs] success to start the backup.')
            self.backup_ipfs_upload_dbfiles(did, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info('[backup_main: ipfs] success to upload database files.')
            self.backup_ipfs_cids(did, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info('[backup_main: ipfs] success to backup ipfs cids.')
            self.update_server_state_to(doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN], STATE_FINISH)
            clog().info('[backup_main: ipfs] success to finish the backup process.')
        else:
            vault_root = get_vault_path(did)
            self.backup_files_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info('[backup_main] success to execute backup.')
            checksum_list = get_file_checksum_list(vault_root)
            self.backup_finish(doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN], checksum_list)
            clog().info('[backup_main] success to finish backup.')

        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        clog().info('[backup_main] success to backup really.')

    def restore(self, did):
        clog().info('[restore_main] enter restore().')

        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {USER_DID: did})
        if self.is_ipfs:
            self.restore_ipfs_download_dbfiles(did, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info('[restore_main: ipfs] success to download database files.')
            cli.import_mongodb(did)
            clog().info('[restore_main: ipfs] success to import mongodb database.')
            self.restore_ipfs_pin_cids(did)
            clog().info('[restore_main: ipfs] success to pin ipfs cids.')
        else:
            vault_root = get_vault_path(did)
            if not vault_root.exists():
                create_full_path_dir(vault_root)
            clog().info(f'[restore_main] success to get vault root path.')
            self.restore_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info(f'[restore_main] success to execute restore.')
            self.restore_finish(did, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
            clog().info(f'[restore_main] success to restore finish.')
            cli.import_mongodb(did)

        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        clog().info('[restore_main] success to restore really.')

    def backup_files_really(self, vault_root, host_url, access_token):
        remote_files = self.http.get(host_url + URL_BACKUP_FILES, access_token)['backup_files']
        local_files = fm.get_file_checksum_list(vault_root)
        new_files, patch_files, delete_files = self.diff_files(local_files, remote_files)
        self.backup_new_files(host_url, access_token, vault_root, new_files)
        self.backup_patch_files(host_url, access_token, vault_root, patch_files)
        self.backup_delete_files(host_url, access_token, vault_root, delete_files)

    def restore_really(self, vault_root, host_url, access_token):
        remote_files = self.http.get(host_url + URL_BACKUP_FILES, access_token)['backup_files']
        local_files = fm.get_file_checksum_list(vault_root)
        new_files, patch_files, delete_files = self.diff_files(remote_files, local_files)
        self.restore_new_files(host_url, access_token, vault_root, new_files)
        self.restore_patch_files(host_url, access_token, vault_root, patch_files)
        self.restore_delete_files(host_url, access_token, vault_root, delete_files)

    def backup_finish(self, host_url, access_token, checksum_list):
        self.http.post(host_url + URL_BACKUP_FINISH, access_token, {'checksum_list': checksum_list}, is_body=False)

    def diff_files(self, base_files, target_files):
        """
        Diff two file list from base to target. Every files list contains item (name, checksum).
        """
        b_files, t_files = dict((n, c) for c, n in base_files), dict((n, c) for c, n in target_files)
        new_files = [n for n, c in b_files.items() if n not in t_files]
        patch_files = [n for n, c in b_files.items() if n in t_files and c != t_files[n]]
        delete_files = [n for n, c in t_files.items() if n not in b_files]
        return new_files, patch_files, delete_files

    def backup_new_files(self, host_url, access_token, vault_root: Path, new_files):
        for name in new_files:
            self.http.put_file(host_url + URL_BACKUP_FILE + f'?file={name}', access_token,
                               (vault_root / name).resolve())

    def restore_new_files(self, host_url, access_token, vault_root: Path, new_files):
        for name in new_files:
            self.http.get_to_file(host_url + URL_BACKUP_FILE + f'?file={name}', access_token,
                                  (vault_root / name).resolve())

    def backup_patch_files(self, host_url, access_token, vault_root: Path, patch_files):
        for name in patch_files:
            hashes = self.get_remote_file_hashes(host_url, access_token, name)
            pickle_data = fm.get_rsync_data((vault_root / name).resolve(), hashes)
            self.http.post(host_url + URL_BACKUP_PATCH_FILE + f'?file={name}', access_token, pickle_data,
                           is_json=False, is_body=False)

    def restore_patch_files(self, host_url, access_token, vault_root: Path, patch_files):
        for name in patch_files:
            full_name = (vault_root / name).resolve()
            hashes = fm.get_hashes_by_file(full_name)
            pickle_data = self.http.post_to_pickle_data(host_url + URL_BACKUP_PATCH_DELTA + f'?file={name}',
                                                        access_token, hashes)
            fm.apply_rsync_data(full_name, pickle_data)

    def backup_delete_files(self, host_url, access_token, vault_root: Path, delete_files):
        for name in delete_files:
            self.http.delete(host_url + URL_BACKUP_FILE + f'?file={name}', access_token)

    def restore_delete_files(self, host_url, access_token, vault_root: Path, delete_files):
        for name in delete_files:
            fm.delete_file((vault_root / name).resolve())

    def get_remote_file_hashes(self, host_url, access_token, name):
        r = self.http.get(host_url + URL_BACKUP_PATCH_HASH + f'?file={name}', access_token, is_body=False)
        return fm.get_hashes_by_lines(r.iter_lines(chunk_size=CHUNK_SIZE))

    def delete_mongodb_data(self, did):
        mongodb_root = get_save_mongo_db_path(did)
        if mongodb_root.exists():
            shutil.rmtree(mongodb_root)

    def execute_restore(self, did, credential_info, access_token):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {USER_DID: did},
                              {"$set": {USER_DID: did,
                                        VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
                                        VAULT_BACKUP_INFO_TYPE: VAULT_BACKUP_INFO_TYPE_HIVE_NODE,
                                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp(),
                                        VAULT_BACKUP_INFO_DRIVE: credential_info['targetHost'],
                                        VAULT_BACKUP_INFO_TOKEN: access_token}},
                              options={'upsert': True}, is_create=True)

        if self.hive_setting.BACKUP_IS_SYNC:
            self.__class__.restore_main(did, self)
        else:
            _thread.start_new_thread(self.__class__.restore_main, (did, self))

    def restore_finish(self, did, host_url, access_token):
        body = self.http.get(host_url + URL_RESTORE_FINISH, access_token)
        checksum_list = body["checksum_list"]
        vault_root = get_vault_path(did)
        if not vault_root.exists():
            create_full_path_dir(vault_root)

        local_checksum_list = get_file_checksum_list(vault_root)
        for checksum in checksum_list:
            if checksum not in local_checksum_list:
                raise BadRequestException(msg='Failed to finish restore.')

    def get_state(self, did):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {USER_DID: did}, is_create=True)
        state, result = 'stop', 'success'
        if doc:
            state, result = doc[VAULT_BACKUP_INFO_STATE], doc[VAULT_BACKUP_INFO_MSG]
        return {'state': state, 'result': result}

    def backup_ipfs_cids(self, did, host_url, access_token):
        total_size, cids = fm.get_file_cids(did)
        if not cids:
            return
        self.http.post(host_url + URL_IPFS_BACKUP_PIN_CIDS, access_token,
                       {'total_size': total_size, 'cids': cids}, is_body=False)

    def backup_ipfs_upload_dbfiles(self, did, host_url, access_token):
        database_dir = get_save_mongo_db_path(did)
        if not database_dir.exists():
            # this means no user databases
            return
        for dir_root, dir_names, filenames in os.walk(database_dir.as_posix()):
            for name in filenames:
                if not name.endswith(BACKUP_FILE_SUFFIX):
                    # skip none backup files.
                    continue
                self.http.put_file(host_url + URL_BACKUP_FILE + f'?file={name}', access_token,
                                   Path(dir_root) / name)
            # no need recursive
            break

    def restore_ipfs_download_dbfiles(self, did, host_url, access_token):
        body = self.http.get(host_url + URL_IPFS_BACKUP_GET_DBFILES, access_token)
        if not body['files']:
            return
        if body['origin_size'] > fm.get_vault_max_size(did):
            raise InsufficientStorageException('No enough space for restore.')
        database_dir = get_save_mongo_db_path(did)
        for name in body['files']:
            self.http.get_to_file(f'{host_url}{URL_BACKUP_FILE}?file={name}', access_token, database_dir / name)

    def restore_ipfs_pin_cids(self, did):
        _, cids = fm.get_file_cids(did)
        for cid in cids:
            fm.ipfs_pin_cid(cid)

    def update_server_state_to(self, host_url, access_token, state, vault_size=0):
        self.http.post(f'{host_url}{URL_IPFS_BACKUP_STATE}?to={state}&vault_size={vault_size}',
                       access_token, None, is_body=False)


class BackupServer:
    def __init__(self, app=None, hive_setting=None, is_ipfs=False):
        self.http_server = HttpServer()
        self.is_ipfs = is_ipfs
        self.client = BackupClient(app, hive_setting, is_ipfs=is_ipfs)

    def _check_auth_backup(self, is_raise=True, is_create=False, is_check_size=False):
        did, app_did = check_auth2()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {VAULT_BACKUP_SERVICE_DID: did},
                                  is_create=is_create, is_raise=False)
        if is_raise and not doc:
            raise BackupNotFoundException()
        if is_raise and is_check_size and doc \
                and doc[VAULT_BACKUP_SERVICE_USE_STORAGE] > doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            raise InsufficientStorageException(msg='No more available space for backup.')
        return did, app_did, doc

    def _subscribe_free(self):
        did, app_did, doc = self._check_auth_backup(is_raise=False, is_create=True)
        if doc:
            raise AlreadyExistsException('The backup service is already subscribed.')
        return self._get_vault_info(self._create_backup(did, PaymentConfig.get_free_backup_info()))

    def _create_backup(self, did, price_plan):
        now = datetime.utcnow().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        # there is no use of database for backup vault.
        doc = {VAULT_BACKUP_SERVICE_DID: did,
               VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1000 * 1000,
               VAULT_BACKUP_SERVICE_USE_STORAGE: 0,
               ORIGINAL_SIZE: 0,
               VAULT_BACKUP_SERVICE_START_TIME: now,
               VAULT_BACKUP_SERVICE_END_TIME: end_time,
               STATE: STATE_RUNNING,
               VAULT_BACKUP_SERVICE_MODIFY_TIME: now,
               VAULT_BACKUP_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_BACKUP_SERVICE_USING: price_plan['name']
               }
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, doc, is_create=True)
        return doc

    def _get_vault_info(self, doc):
        return {
            'pricing_plan': doc[VAULT_BACKUP_SERVICE_USING],
            'service_did': get_current_node_did_string(),
            'storage_quota': int(doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc[VAULT_BACKUP_SERVICE_USE_STORAGE]),
            'created': cli.timestamp_to_epoch(doc[VAULT_BACKUP_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc['modified']),
        }

    @hive_restful_response
    def subscribe(self):
        return self._subscribe_free()

    @hive_restful_response
    def unsubscribe(self):
        did, _, doc = self._check_auth_backup(is_raise=False)
        if not doc:
            return
        backup_root = get_vault_backup_path(did)
        if backup_root.exists():
            shutil.rmtree(backup_root)
        cli.delete_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_SERVICE_COL,
                              {VAULT_BACKUP_SERVICE_DID: did},
                              is_check_exist=False)

    @hive_restful_response
    def activate(self):
        raise NotImplementedException()

    @hive_restful_response
    def deactivate(self):
        raise NotImplementedException()

    @hive_restful_response
    def get_info(self):
        _, _, doc = self._check_auth_backup(is_create=True)
        return self._get_vault_info(doc)

    @hive_restful_response
    def get_backup_service(self):
        _, _, doc = self._check_auth_backup(is_create=True)
        del doc["_id"]
        return doc

    @hive_restful_response
    def backup_finish(self, checksum_list):
        did, _, doc = self._check_auth_backup()

        backup_root = get_vault_backup_path(did)
        # TODO: remove this check.
        if not backup_root.exists():
            create_full_path_dir(backup_root)

        local_checksum_list = get_file_checksum_list(backup_root)
        for checksum in checksum_list:
            if checksum not in local_checksum_list:
                raise BadRequestException(msg='Failed to finish backup process.')

        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_SERVICE_COL,
                              {VAULT_BACKUP_SERVICE_DID: did},
                              {"$set": {VAULT_BACKUP_SERVICE_USE_STORAGE: get_dir_size(backup_root.as_posix(), 0)}})

    @hive_restful_response
    def backup_files(self):
        did, _, _ = self._check_auth_backup()
        return {'backup_files': fm.get_file_checksum_list(get_vault_backup_path(did))}

    @hive_stream_response
    def backup_get_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self._check_auth_backup()
        return self.http_server.create_range_request((get_vault_backup_path(did) / file_name).resolve())

    @hive_restful_response
    def backup_upload_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        is_ipfs = file_name.endswith(BACKUP_FILE_SUFFIX)
        did, _, backup = self._check_auth_backup(is_check_size=is_ipfs)
        dst_file = (get_vault_backup_path(did) / file_name).resolve()
        fm.write_file_by_request_stream(dst_file)
        if is_ipfs:
            self.ipfs_increase_used_size(backup, dst_file.stat().st_size)

    @hive_restful_response
    def backup_delete_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self._check_auth_backup()
        fm.delete_vault_file(did, file_name)

    @hive_stream_response
    def backup_get_file_hash(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self._check_auth_backup()
        return fm.get_hashes_by_file((get_vault_backup_path(did) / file_name).resolve())

    @hive_stream_response
    def backup_get_file_delta(self, file_name):
        if not file_name:
            raise InvalidParameterException(msg='The file name must provide.')

        did, _, _ = self._check_auth_backup()

        data = request.get_data()
        hashes = fm.get_hashes_by_lines(list() if not data else data.split(b'\n'))
        return fm.get_rsync_data((get_vault_backup_path(did) / file_name).resolve(), hashes)

    @hive_restful_response
    def backup_patch_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self._check_auth_backup()

        temp_file = gene_temp_file_name()
        fm.write_file_by_request_stream(temp_file)
        pickle_data = fm.read_rsync_data_from_file(temp_file)
        temp_file.unlink()
        fm.apply_rsync_data((get_vault_backup_path(did) / file_name).resolve(), pickle_data)

    @hive_restful_response
    def restore_finish(self):
        did, _, _ = self._check_auth_backup()
        backup_root = get_vault_backup_path(did)
        checksum_list = list()
        if backup_root.exists():
            checksum_list = get_file_checksum_list(backup_root)
        return {'checksum_list': checksum_list}

    @hive_restful_response
    def ipfs_backup_state(self, to, vault_size):
        if to != STATE_RUNNING and to != STATE_FINISH:
            raise InvalidParameterException(f'Invalid parameter to = {to}')

        did, _, backup = self._check_auth_backup()
        if backup[VAULT_BACKUP_SERVICE_MAX_STORAGE] < vault_size:
            raise InsufficientStorageException('No more space for the backup process.')
        self.ipfs_update_state_really(did, to, vault_size)

    def ipfs_update_state_really(self, did, to, vault_size=0):
        update = {'$set': {STATE: to, VAULT_BACKUP_SERVICE_MODIFY_TIME: datetime.utcnow().timestamp()}}
        if to == STATE_RUNNING:
            # This is the start of the backup processing.
            update['$set'][VAULT_BACKUP_SERVICE_USE_STORAGE] = 0
            update['$set'][ORIGINAL_SIZE] = vault_size
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {DID: did}, update)

    @hive_restful_response
    def ipfs_pin_cids(self, total_size, cids):
        did, _, backup = self._check_auth_backup(is_check_size=True)
        if backup[VAULT_BACKUP_SERVICE_USE_STORAGE] + total_size > backup[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            raise InsufficientStorageException(msg='No enough space to backup files.')

        for cid in cids:
            if not cid:
                continue
            fm.ipfs_pin_cid(cid)
        self.ipfs_increase_used_size(backup, total_size)

    @hive_restful_response
    def ipfs_get_dbfiles(self):
        did, _, backup = self._check_auth_backup()
        vault_dir = get_vault_backup_path(did)
        return {
            'origin_size': backup[ORIGINAL_SIZE],
            'files': [name.name for name in vault_dir.iterdir() if name.suffix == BACKUP_FILE_SUFFIX]
        }

    @hive_restful_response
    def ipfs_promotion(self):
        did, app_did, backup = self._check_auth_backup()
        if backup[STATE] != STATE_FINISH:
            raise BadRequestException(msg='No backup data exists.')

        from src.view.subscription import vault_subscription
        vault = vault_subscription.get_checked_vault(did, is_raise=False)
        if vault:
            raise AlreadyExistsException(msg='The vault already exists, no need promotion.')

        vault_subscription.create_vault(did, vault_subscription.get_price_plan('vault', 'Free'), True)
        cli.import_mongodb_in_backup_server(did)

    def ipfs_increase_used_size(self, backup, size, is_reset=False):
        update = {'$set': dict()}
        if is_reset:
            update['$set'][VAULT_BACKUP_SERVICE_USE_STORAGE] = 0
        else:
            update['$set'][VAULT_BACKUP_SERVICE_USE_STORAGE] = backup[VAULT_BACKUP_SERVICE_USE_STORAGE] + size
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {DID: backup[DID]}, update)
