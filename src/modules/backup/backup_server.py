# -*- coding: utf-8 -*-
import _thread
import logging
import shutil
import traceback
from datetime import datetime
from pathlib import Path

from flask import request

from src.utils_v1.common import get_file_checksum_list, gene_temp_file_name, \
    create_full_path_dir
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, VAULT_BACKUP_INFO_STATE, DID, \
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
    URL_BACKUP_PATCH_HASH, URL_BACKUP_PATCH_FILE, URL_RESTORE_FINISH, URL_BACKUP_PATCH_DELTA
from src.utils.file_manager import fm
from src.utils.http_response import hive_restful_response, hive_stream_response
from src.utils.singleton import Singleton
from src.utils_v1.auth import get_did_string


def clog():
    return logging.getLogger('BACKUP_CLIENT')


def slog():
    return logging.getLogger('BACKUP_SERVER')


class BackupClient:
    def __init__(self, app=None, hive_setting=None):
        self.http = HttpClient()
        self.backup_thread = None
        self.hive_setting = hive_setting
        self.mongo_host, self.mongo_port = None, None
        if hive_setting:
            self.mongo_host, self.mongo_port = self.hive_setting.MONGO_HOST, self.hive_setting.MONGO_PORT
        self.auth = Auth(app, hive_setting)

    def check_backup_status(self, did, is_restore=False):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did}, is_create=True)
        if doc and doc[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP \
                and doc[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
            raise BackupIsInProcessingException('The backup/restore is in process.')

        if is_restore and not (doc[VAULT_BACKUP_INFO_STATE] == VAULT_BACKUP_STATE_STOP
                               and doc[VAULT_BACKUP_INFO_MSG] == VAULT_BACKUP_MSG_SUCCESS):
            raise BadRequestException(msg='No successfully backup for restore.')

    def get_backup_service_info(self, credential, credential_info):
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = \
            self.auth.backup_client_sign_in(target_host, credential, 'DIDBackupAuthResponse')
        access_token = self.auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)
        return self.http.get(target_host + URL_BACKUP_SERVICE, access_token), access_token

    def execute_backup(self, did, credential_info, backup_service_info, access_token):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {DID: did},
                              {"$set": {DID: did,
                                        VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
                                        VAULT_BACKUP_INFO_TYPE: VAULT_BACKUP_INFO_TYPE_HIVE_NODE,
                                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp(),
                                        VAULT_BACKUP_INFO_DRIVE: credential_info['targetHost'],
                                        VAULT_BACKUP_INFO_TOKEN: access_token}},
                              options={'upsert': True}, is_create=True)

        vault_size = fm.get_vault_storage_size(did)
        if vault_size > backup_service_info[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            raise InsufficientStorageException(msg='Insufficient storage to execute backup.')

        clog().debug('start new thread for backup processing.')

        _thread.start_new_thread(self.__class__.backup_main, (did, self))

    def update_backup_state(self, did, state, msg):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {DID: did},
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
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)
        clog().info('[backup_main] leave backup thread.')

    @staticmethod
    def restore_main(did, client):
        try:
            clog().info(f'[restore_main] enter restore thread, {did}, {client}.')
            client.restore(did)
        except Exception as e:
            clog().error(f'[restore_main] Failed to restore really: {traceback.format_exc()}')
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)

    def backup(self, did):
        clog().info('[backup_main] enter backup().')
        cli.export_mongodb(did)
        clog().info('[backup_main] success to export mongodb data.')
        vault_root = get_vault_path(did)
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did})
        clog().info('[backup_main] success to get backup info.')
        self.backup_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
        clog().info('[backup_main] success to execute backup.')

        checksum_list = get_file_checksum_list(vault_root)
        self.backup_finish(doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN], checksum_list)
        clog().info('[backup_main] success to finish backup.')
        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        clog().info('[backup_main] success to backup really.')

    def restore(self, did):
        clog().info('[backup_main] enter restore().')
        vault_root = get_vault_path(did)
        if not vault_root.exists():
            create_full_path_dir(vault_root)
        clog().info(f'[restore_main] success to get vault root path.')
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did})
        self.restore_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
        clog().info(f'[restore_main] success to execute restore.')
        self.restore_finish(did, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
        clog().info(f'[restore_main] success to restore finish.')

        cli.import_mongodb(did)
        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        clog().info('[restore_main] success to backup really.')

    def backup_really(self, vault_root, host_url, access_token):
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

    def execute_restore(self, did, credential_info, backup_service_info, access_token):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {DID: did},
                              {"$set": {DID: did,
                                        VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
                                        VAULT_BACKUP_INFO_TYPE: VAULT_BACKUP_INFO_TYPE_HIVE_NODE,
                                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp(),
                                        VAULT_BACKUP_INFO_DRIVE: credential_info['targetHost'],
                                        VAULT_BACKUP_INFO_TOKEN: access_token}},
                              options={'upsert': True}, is_create=True)

        # TODO: check the vault storage has enough space to restore.
        # use_storage = get_vault_used_storage(did)
        # if use_storage > backup_service_info[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
        #     raise InsufficientStorageException(msg='Insufficient storage to execute backup.')

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
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did}, is_create=True)
        state, result = 'stop', 'success'
        if doc:
            state, result = doc[VAULT_BACKUP_INFO_STATE], doc[VAULT_BACKUP_INFO_MSG]
        return {'state': state, 'result': result}


class BackupServer(metaclass=Singleton):
    def __init__(self):
        self.http_server = HttpServer()

    def _check_auth_backup(self, is_raise=True, is_create=False):
        did, app_did = check_auth2()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {VAULT_BACKUP_SERVICE_DID: did},
                                  is_create=is_create, is_raise=False)
        if is_raise and not doc:
            raise BackupNotFoundException()
        return did, app_did, doc

    def _subscribe_free(self):
        did, app_did, doc = self._check_auth_backup(is_raise=False, is_create=True)
        if doc:
            raise AlreadyExistsException('The backup vault is already subscribed.')
        return self._get_vault_info(self._create_backup(did, PaymentConfig.get_free_backup_info()))

    def _create_backup(self, did, price_plan):
        now = datetime.utcnow().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        # there is no use of database for backup vault.
        doc = {VAULT_BACKUP_SERVICE_DID: did,
               VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1000 * 1000,
               VAULT_BACKUP_SERVICE_USE_STORAGE: 0,
               VAULT_BACKUP_SERVICE_START_TIME: now,
               VAULT_BACKUP_SERVICE_END_TIME: end_time,
               VAULT_BACKUP_SERVICE_MODIFY_TIME: now,
               VAULT_BACKUP_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_BACKUP_SERVICE_USING: price_plan['name']
               }
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, doc, is_create=True)
        return doc

    def _get_vault_info(self, doc):
        return {
            'pricing_plan': doc[VAULT_BACKUP_SERVICE_USING],
            'service_did': get_did_string(),
            'storage_quota': int(doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc[VAULT_BACKUP_SERVICE_USE_STORAGE]),
            'created': cli.timestamp_to_epoch(doc[VAULT_BACKUP_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_BACKUP_SERVICE_MODIFY_TIME]),
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

        did, _, _ = self._check_auth_backup()
        fm.write_file_by_request_stream((get_vault_backup_path(did) / file_name).resolve())

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
