# -*- coding: utf-8 -*-
import _thread
import pickle
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import requests
from flask import request

from hive.main.view import h_auth
from hive.util.common import get_file_checksum_list, deal_dir, get_file_md5_info, gene_temp_file_name, \
    create_full_path_dir
from hive.util.constants import DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, VAULT_BACKUP_INFO_STATE, DID, \
    VAULT_BACKUP_INFO_TIME, VAULT_BACKUP_INFO_TYPE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, VAULT_BACKUP_INFO_MSG, \
    VAULT_BACKUP_INFO_DRIVE, VAULT_BACKUP_INFO_TOKEN, VAULT_BACKUP_SERVICE_MAX_STORAGE, APP_ID, CHUNK_SIZE, \
    VAULT_BACKUP_SERVICE_COL, VAULT_BACKUP_SERVICE_DID, VAULT_BACKUP_SERVICE_USE_STORAGE, \
    VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, VAULT_BACKUP_SERVICE_MODIFY_TIME, \
    VAULT_BACKUP_SERVICE_STATE, VAULT_BACKUP_SERVICE_USING
from hive.util.did_file_info import get_vault_path, get_dir_size
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, get_save_mongo_db_path
from hive.util.flask_rangerequest import RangeRequest
from hive.util.payment.payment_config import PaymentConfig
from hive.util.payment.vault_backup_service_manage import get_vault_backup_path
from hive.util.payment.vault_service_manage import get_vault_used_storage, VAULT_SERVICE_STATE_RUNNING
from hive.util.pyrsync import rsyncdelta, gene_blockchecksums
from hive.util.vault_backup_info import VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS, \
    VAULT_BACKUP_MSG_FAILED, VAULT_BACKUP_STATE_RESTORE
from src.modules.scripting.scripting import check_auth
from src.utils.database_client import cli
from src.utils.http_response import BackupIsInProcessingException, InsufficientStorageException, \
    InvalidParameterException, BadRequestException, AlreadyExistsException, BackupNotFoundException, \
    FileNotFoundException
from src.view import URL_BACKUP_SERVICE, URL_BACKUP_FINISH, URL_BACKUP_FILES, URL_BACKUP_FILE, \
    URL_BACKUP_PATCH_HASH, URL_BACKUP_PATCH_FILE, URL_RESTORE_FINISH
from src.view.auth import auth


class BackupClient:
    def __init__(self, hive_setting):
        self.hive_setting = hive_setting
        self.mongo_host, self.mongo_port = self.hive_setting.MONGO_HOST, self.hive_setting.MONGO_PORT

    def http_get(self, url, access_token, is_body=True, options=None):
        try:
            headers = {"Content-Type": "application/json", "Authorization": "token " + access_token}
            r = requests.get(url, headers=headers, **(options if options else {}))
            if r.status_code != 200:
                raise InvalidParameterException(msg=f'Failed to GET with status code: {r.status_code}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(msg=f'Failed to GET with exception: {str(e)}')

    def http_post(self, url, access_token, body, is_json=True):
        try:
            headers = {"Authorization": "token " + access_token}
            if is_json:
                headers['Content-Type'] = 'application/json'
            r = requests.post(url, headers=headers, json=body) \
                if is_json else requests.post(url, headers=headers, data=body)
            if r.status_code != 201:
                raise InvalidParameterException(f'Failed to POST with status code: {r.status_code}')
            return r.json()
        except Exception as e:
            raise InvalidParameterException(f'Failed to POST with exception: {str(e)}')

    def http_put(self, url, access_token, body):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.put(url, headers=headers, data=body)
            if r.status_code != 200:
                raise InvalidParameterException(f'Failed to PUT with status code: {r.status_code}')
            return r.json()
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT with exception: {str(e)}')

    def http_delete(self, url, access_token):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.delete(url, headers=headers)
            if r.status_code != 200:
                raise InvalidParameterException(f'Failed to PUT with status code: {r.status_code}')
            return r.json()
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT with exception: {str(e)}')

    def check_backup_status(self, did):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did})
        if doc and doc[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP:
            # if doc[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
            raise BackupIsInProcessingException()

    def get_backup_service_info(self, credential, credential_info):
        target_host = credential_info['targetHost']
        challenge_response, backup_service_instance_did = auth.backup_client_sign_in(target_host, credential,
                                                                              'DIDBackupAuthResponse')
        access_token = auth.backup_client_auth(target_host, challenge_response, backup_service_instance_did)
        return self.http_get(target_host + URL_BACKUP_SERVICE, access_token), access_token

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
                              options={'upsert': True})

        use_storage = get_vault_used_storage(did)
        if use_storage > backup_service_info[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            raise InsufficientStorageException(msg='Insufficient storage to execute backup.')

        _thread.start_new_thread(self.__class__.backup_main, (did, self))

    def update_backup_state(self, did, state, msg):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {DID: did},
                              {"$set": {VAULT_BACKUP_INFO_STATE: state,
                                        VAULT_BACKUP_INFO_MSG: msg,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp()}})

    def export_mongodb_data(self, did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[DID], did_info[APP_ID])

    def import_mongodb(self, did):
        mongodb_root = get_save_mongo_db_path(did)
        if not mongodb_root.exists():
            return False
        line2 = f'mongorestore -h {self.mongo_host} --port {self.mongo_port} --drop {mongodb_root}'
        return_code = subprocess.call(line2, shell=True)
        if return_code != 0:
            raise BadRequestException(msg='Failed to restore mongodb data.')

    @staticmethod
    def backup_main(did, client):
        try:
            client.backup(did)
        except Exception as e:
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)

    def backup(self, did):
        self.export_mongodb_data(did)
        vault_root = get_vault_path(did)
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did})
        self.backup_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])

        checksum_list = get_file_checksum_list(vault_root)
        self.backup_finish(doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN], checksum_list)
        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)

    def restore(self, did):
        vault_root = get_vault_path(did)
        if not vault_root.exists():
            create_full_path_dir(vault_root)

        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, {DID: did})
        self.restore_really(vault_root, doc[VAULT_BACKUP_INFO_DRIVE], doc[VAULT_BACKUP_INFO_TOKEN])
        self.restore_finish(did, doc[VAULT_BACKUP_INFO_DRIVE] + URL_RESTORE_FINISH,
                            doc[VAULT_BACKUP_INFO_TOKEN])

        self.import_mongodb(did)
        self.delete_mongodb_data(did)
        self.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)

    def backup_really(self, vault_root, host_url, access_token):
        remote_files = self.http_get(host_url + URL_BACKUP_FILES, access_token)['backup_files']
        local_files = deal_dir(vault_root.as_posix(), get_file_md5_info)
        new_files, patch_files, delete_files = self.diff_backup_files(remote_files, local_files, vault_root)
        self.backup_new_files(host_url, access_token, new_files)
        self.backup_patch_files(host_url, access_token, patch_files)
        self.backup_delete_files(host_url, access_token, delete_files)

    def restore_really(self, vault_root, host_url, access_token):
        remote_files = self.http_get(host_url + URL_BACKUP_FILES, access_token)['backup_files']
        local_files = deal_dir(vault_root.as_posix(), get_file_md5_info)
        new_files, patch_files, delete_files = self.diff_restore_files(remote_files, local_files, vault_root)
        self.restore_new_files(host_url, access_token, new_files)
        self.restore_patch_files(host_url, access_token, patch_files)
        self.restore_delete_files(host_url, access_token, delete_files)

    def backup_finish(self, host_url, access_token, checksum_list):
        self.http_post(host_url + URL_BACKUP_FINISH, access_token, {'checksum_list': checksum_list})

    def diff_backup_files(self, remote_files, local_files, vault_root):
        remote_files_d = dict((d[1], d[0]) for d in remote_files)  # name: checksum
        # name: checksum, full_name
        local_files_d = dict((Path(d[1]).relative_to(vault_root).as_posix(), (d[0], d[1])) for d in local_files)
        new_files = [[d[1], n] for n, d in local_files_d.items() if n not in remote_files_d]
        patch_files = [[d[1], n] for n, d in local_files_d.items() if n in remote_files_d and remote_files_d[n] != d[0]]
        delete_files = [n for n in remote_files_d.keys() if n not in local_files_d]
        return new_files, patch_files, delete_files

    def diff_restore_files(self, remote_files, local_files, vault_root):
        # name: checksum, full_name
        remote_files_d = dict((d[1], (d[0], (vault_root / d[1]).as_posix())) for d in remote_files)
        local_files_d = dict((Path(d[1]).relative_to(vault_root).as_posix(), (d[0], d[1])) for d in local_files)
        new_files = [[d[1], n] for n, d in remote_files_d.items() if n not in local_files_d]
        patch_files = [[d[1], n] for n, d in remote_files_d.items() if n in local_files_d and local_files_d[n][0] != d[0]]
        delete_files = [d[1] for n, d in local_files_d.items() if n not in remote_files_d]
        return new_files, patch_files, delete_files

    def backup_new_files(self, host_url, access_token, new_files):
        for info in new_files:
            src_file, dst_file = info[0], info[1]
            with open(src_file, 'br') as f:
                self.http_put(host_url + URL_BACKUP_FILE + f'?file={dst_file}', access_token, f)

    def restore_new_files(self, host_url, access_token, new_files):
        for info in new_files:
            name, full_name = info[0], Path(info[1])
            full_name.resolve()
            temp_file = gene_temp_file_name()
            if not full_name.parent.exists() and not create_full_path_dir(full_name.parent):
                # TODO: fix this
                pass

            r = self.http_get(host_url + URL_BACKUP_FILE + f'?file={name}', access_token, is_body=False,
                              options={'stream': True})
            with open(temp_file, 'bw') as f:
                f.seek(0)
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

            if full_name.exists():
                full_name.unlink()
            shutil.move(temp_file.as_posix(), full_name.as_posix())

    def backup_patch_files(self, host_url, access_token, patch_files):
        for full_name, name in patch_files:
            hashes = self.get_remote_file_hashes(host_url, access_token, name)
            with open(full_name, "rb") as f:
                patch_data = rsyncdelta(f, hashes, blocksize=CHUNK_SIZE)

            temp_file = gene_temp_file_name()
            with open(temp_file, "wb") as f:
                pickle.dump(patch_data, f)

            with open(temp_file.as_posix(), 'rb') as f:
                self.http_post(host_url + URL_BACKUP_PATCH_FILE + f'?file={full_name}', body=f, is_json=False)

            temp_file.unlink()

    def restore_delete_files(self, host_url, access_token, delete_files):
        for full_name in delete_files:
            full_name.unlink()

    def get_remote_file_hashes(self, host_url, access_token, name):
        r = self.http_get(host_url + URL_BACKUP_PATCH_HASH + f'?file={name}', access_token, is_body=False)
        hashes = list()
        for line in r.iter_lines(chunk_size=CHUNK_SIZE):
            parts = line.split(b',')
            hashes.append((int(parts[0]), parts[1].decode("utf-8")))
        return hashes

    def backup_delete_files(self, host_url, access_token, delete_files):
        for name in delete_files:
            self.http_delete(host_url + URL_BACKUP_FILE + f'?file={name}', access_token)

    def delete_mongodb_data(self, did):
        mongodb_root = get_save_mongo_db_path(did)
        if mongodb_root.exists():
            shutil.rmtree(mongodb_root)

    def execute_restore(self, did, credential_info, backup_service_info, access_token):
        cli.update_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_INFO_COL,
                              {DID: did},
                              {"$set": {DID: did,
                                        VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_RESTORE,
                                        VAULT_BACKUP_INFO_TYPE: VAULT_BACKUP_INFO_TYPE_HIVE_NODE,
                                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                                        VAULT_BACKUP_INFO_TIME: datetime.utcnow().timestamp(),
                                        VAULT_BACKUP_INFO_DRIVE: credential_info['targetHost'],
                                        VAULT_BACKUP_INFO_TOKEN: access_token}},
                              options={'upsert': True})

        # use_storage = get_vault_used_storage(did)
        # if use_storage > backup_service_info[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
        #     raise InsufficientStorageException(msg='Insufficient storage to execute backup.')

        _thread.start_new_thread(self.__class__.restore_main, (did, self))

    @staticmethod
    def restore_main(did, client):
        try:
            client.restore(did)
        except Exception as e:
            client.update_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_FAILED)

    def restore_finish(self, did, host_url, access_token):
        # INFO: skip this step.
        pass


class BackupServer:
    def __init__(self):
        pass

    def __check_auth_backup(self, is_raise=True, is_create=False):
        did, app_did = check_auth()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {VAULT_BACKUP_SERVICE_DID: did},
                                  is_create=is_create)
        if is_raise and not doc:
            raise BackupNotFoundException()
        return did, app_did, doc

    def subscribe_free(self):
        did, app_did, doc = self.__check_auth_backup(is_raise=False, is_create=True)
        if doc:
            raise AlreadyExistsException('The backup vault is already subscribed.')
        return self.__get_vault_info(self.__create_backup(did, PaymentConfig.get_free_backup_info()))

    def __create_backup(self, did, price_plan):
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

    def __get_vault_info(self, doc):
        return {
            'pricing_plan': doc[VAULT_BACKUP_SERVICE_USING],
            'service_did': h_auth.get_did_string(),
            'storage_quota': int(doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc[VAULT_BACKUP_SERVICE_USE_STORAGE]),
            'created': cli.timestamp_to_epoch(doc[VAULT_BACKUP_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_BACKUP_SERVICE_MODIFY_TIME]),
        }

    def unsubscribe(self):
        did, _, doc = self.__check_auth_backup(is_raise=False)
        if not doc:
            return
        # TODO: delete backup storage for backup files.
        cli.delete_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_SERVICE_COL,
                              {VAULT_BACKUP_SERVICE_DID: did},
                              is_check_exist=False)

    def get_info(self):
        _, _, doc = self.__check_auth_backup()
        return self.__get_vault_info(doc)

    def get_backup_service(self):
        did, _, doc = self.__check_auth_backup()

        # backup_root = get_vault_backup_path(did)
        # if not backup_root.exists():
        #     create_full_path_dir(backup_root)

        del doc["_id"]
        return doc

    def backup_finish(self, checksum_list):
        if not checksum_list:
            raise InvalidParameterException(msg='checksum_list must provide.')

        did, _, doc = self.__check_auth_backup()

        backup_root = get_vault_backup_path(did)
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

    def backup_files(self):
        did, _, _ = self.__check_auth_backup()

        result = dict()
        backup_root = get_vault_backup_path(did)
        if backup_root.exists():
            md5_list = deal_dir(backup_root.as_posix(), get_file_md5_info)
            result['backup_files'] = [(md5[0], Path(md5[1]).relative_to(backup_root).as_posix()) for md5 in md5_list]
        return result

    def backup_get_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self.__check_auth_backup()

        backup_root = get_vault_backup_path(did)
        full_name = (backup_root / file_name).resolve()
        if not full_name.exists() or not full_name.is_file():
            raise FileNotFoundException()

        with open(full_name, 'rb') as f:
            etag = RangeRequest.make_etag(f)
        return RangeRequest(open(full_name, 'rb'),
                            etag=etag,
                            last_modified=datetime.utcnow(),
                            size=full_name.stat().st_size).make_response()

    def backup_upload_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self.__check_auth_backup()
        backup_root = get_vault_backup_path(did)
        full_name = (backup_root / file_name).resolve()
        if not full_name.parent.exists():
            create_full_path_dir(full_name.parent)

        temp_file = gene_temp_file_name()
        with open(temp_file, "bw") as f:
            while True:
                chunk = request.stream.read(CHUNK_SIZE)
                if len(chunk) == 0:
                    break
                f.write(chunk)

        if full_name.exists():
            full_name.unlink()
        shutil.move(temp_file.as_posix(), full_name.as_posix())

    def backup_delete_file(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self.__check_auth_backup()
        backup_root = get_vault_backup_path(did)
        full_name = (backup_root / file_name).resolve()

        if full_name.exists() and full_name.is_file():
            full_name.unlink()

    def backup_get_file_hash(self, file_name):
        if not file_name:
            raise InvalidParameterException()

        did, _, _ = self.__check_auth_backup()
        backup_root = get_vault_backup_path(did)
        full_name = (backup_root / file_name).resolve()
        with open(full_name, 'rb') as f:
            return gene_blockchecksums(f, blocksize=CHUNK_SIZE)
