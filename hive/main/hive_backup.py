import _thread
import json
import logging
import pathlib
import pickle
import shutil
import subprocess
import re
import sys

import requests
from pathlib import Path

from hive.main import view
from hive.util.auth import did_auth
from hive.util.common import did_tail_part, create_full_path_dir, get_host, deal_dir, get_file_md5_info, \
    get_file_checksum_list, gene_temp_file_name
from hive.util.common import did_tail_part, create_full_path_dir, get_host
from hive.util.constants import APP_ID, VAULT_ACCESS_R, HIVE_MODE_TEST, HIVE_MODE_DEV, \
    VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, INTER_BACKUP_SAVE_FINISH_URL, INTER_BACKUP_RESTORE_FINISH_URL, \
    INTER_BACKUP_SERVICE_URL, INTER_BACKUP_FILE_LIST_URL, INTER_BACKUP_FILE_URL, CHUNK_SIZE, \
    INTER_BACKUP_PATCH_HASH_URL, INTER_BACKUP_PATCH_DELTA_URL, INTER_BACKUP_GENE_DELTA_URL
from hive.util.did_file_info import filter_path_root, get_vault_path
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, import_mongo_db, delete_mongo_db_export
from hive.util.error_code import BAD_REQUEST, UNAUTHORIZED, INSUFFICIENT_STORAGE, SUCCESS, NOT_FOUND, CHECKSUM_FAILED, \
    SERVER_SAVE_FILE_ERROR, SERVER_PATCH_FILE_ERROR, INTERNAL_SERVER_ERROR, SERVER_OPEN_FILE_ERROR
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, copy_local_backup_to_vault
from hive.util.payment.vault_service_manage import get_vault_service, get_vault_used_storage, \
    freeze_vault, unfreeze_vault, delete_user_vault_data
from hive.util.pyrsync import rsyncdelta, gene_blockchecksums, patchstream
from hive.util.vault_backup_info import *
from hive.util.rclone_tool import RcloneTool
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, did_post_json_param_pre_proc
from hive.settings import hive_setting


class HiveBackup:
    mode = HIVE_MODE_DEV

    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveBackup")
        self.backup_ftp = None

    def init_app(self, app, mode):
        backup_path = Path(hive_setting.BACKUP_VAULTS_BASE_DIR)
        if not backup_path.exists:
            create_full_path_dir(backup_path)
        self.app = app
        HiveBackup.mode = mode

    # ------------------ common start ----------------------------

    @staticmethod
    def restore_vault_data(did):
        info = get_vault_backup_info(did)
        if not info:
            return None
        update_vault_backup_state(did, VAULT_BACKUP_STATE_RESTORE, VAULT_BACKUP_MSG_SUCCESS)
        vault_folder = get_vault_path(did)
        if not vault_folder.exists():
            create_full_path_dir(vault_folder)

        vault_backup_msg = VAULT_BACKUP_MSG_SUCCESS
        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__restore_google_drive(vault_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            HiveBackup.restore_from_hive_node_start(vault_folder, did,
                                                    info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_TOKEN])
            ret = HiveBackup.restore_backup_finish(did, info[VAULT_BACKUP_INFO_DRIVE] + INTER_BACKUP_RESTORE_FINISH_URL,
                                                   info[VAULT_BACKUP_INFO_TOKEN])
            if not ret:
                vault_backup_msg = VAULT_BACKUP_MSG_FAILED
        else:
            logging.getLogger("HiveBackup").error(
                "restore_vault_data not support backup type:" + info[VAULT_BACKUP_INFO_TYPE])
            info = None

        if vault_backup_msg == VAULT_BACKUP_MSG_SUCCESS:
            import_mongo_db(did)
            update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, vault_backup_msg)
            delete_mongo_db_export(did)
        else:
            update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, vault_backup_msg)
        return info

    @staticmethod
    def export_mongo_db_did(did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[DID], did_info[APP_ID])

    @staticmethod
    def save_vault_data(did):
        info = get_vault_backup_info(did)
        if not info:
            return None
        update_vault_backup_state(did, VAULT_BACKUP_STATE_BACKUP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.export_mongo_db_did(did)
        did_vault_folder = get_vault_path(did)
        vault_backup_msg = VAULT_BACKUP_MSG_SUCCESS
        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__save_google_drive(did_vault_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            checksum_list = get_file_checksum_list(did_vault_folder)
            if not checksum_list:
                logging.getLogger("HiveBackup").error(f"{did} vault data is empty, no need to backup")
            else:
                HiveBackup.save_to_hive_node_start(did_vault_folder, did,
                                                   info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_TOKEN])
                ret = HiveBackup.save_to_hive_node_finish(did,
                                                          info[VAULT_BACKUP_INFO_DRIVE] + INTER_BACKUP_SAVE_FINISH_URL,
                                                          info[VAULT_BACKUP_INFO_TOKEN], checksum_list)
                if not ret:
                    vault_backup_msg = VAULT_BACKUP_MSG_FAILED
        else:
            logging.getLogger("HiveBackup").error(
                "restore_vault_data not support backup type:" + info[VAULT_BACKUP_INFO_TYPE])
            info = None

        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, vault_backup_msg)
        delete_mongo_db_export(did)
        if info:
            # if all ok, we return updated info
            info = get_vault_backup_info(did)
        return info

    # ------------------ common end ----------------------------

    # ------------------ backup to google start ----------------------------
    def __proc_google_drive_param(self):
        did, content, err = did_post_json_param_pre_proc(self.response,
                                                         'token',
                                                         'refresh_token',
                                                         'expiry',
                                                         'client_id',
                                                         'client_secret',
                                                         access_vault=VAULT_ACCESS_R)
        if err:
            return None, None, err

        info = get_vault_backup_info(did)
        if info and info[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP:
            # If sync process more than one day, we think it is failed
            if info[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
                data = dict()
                data["vault_backup_state"] = info[VAULT_BACKUP_INFO_STATE]
                return None, None, self.response.response_ok(data)

        config_data = RcloneTool.get_config_data(content, did)
        drive_name = HiveBackup.gene_did_google_drive_name(did)

        RcloneTool.create_rclone_config_file(drive_name, config_data)
        upsert_vault_backup_info(did, VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE, drive_name)
        return did, drive_name, None

    def save_to_google_drive(self):
        did, drive_name, response = self.__proc_google_drive_param()
        if response:
            return response
        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.save_vault_data, (did,))
        return self.response.response_ok()

    def restore_from_google_drive(self):
        did, drive_name, err = self.__proc_google_drive_param()
        if err:
            return err
        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.restore_vault_data, (did,))
        return self.response.response_ok()

    def get_sync_state(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return self.response.response_err(UNAUTHORIZED, "auth failed")

        info = get_vault_backup_info(did)
        if info:
            if VAULT_BACKUP_INFO_MSG not in info:
                result = VAULT_BACKUP_MSG_SUCCESS
            else:
                result = info[VAULT_BACKUP_INFO_MSG]
            data = {
                "hive_backup_state": info[VAULT_BACKUP_INFO_STATE],
                "result": result
            }
        else:
            data = {
                "hive_backup_state": VAULT_BACKUP_STATE_STOP,
                "result": VAULT_BACKUP_MSG_SUCCESS
            }
        return self.response.response_ok(data)

    @staticmethod
    def gene_did_google_drive_name(did):
        drive = "gdrive_%s" % did_tail_part(did)
        return drive

    @staticmethod
    def __restore_google_drive(did_folder, drive_name):
        rclone_config = RcloneTool.find_rclone_config_file(drive_name)
        if not rclone_config.exists():
            return
        line = f'rclone  --config {rclone_config.as_posix()} sync {drive_name}:elastos_hive_node_data {did_folder.as_posix()}'
        if HiveBackup.mode != HIVE_MODE_TEST:
            subprocess.call(line, shell=True)
        RcloneTool.remove_rclone_config_file(drive_name)

    @staticmethod
    def __save_google_drive(did_folder, drive_name):
        rclone_config = RcloneTool.find_rclone_config_file(drive_name)
        if not rclone_config.exists():
            return
        line = f'rclone --config {rclone_config.as_posix()} sync {did_folder.as_posix()} {drive_name}:elastos_hive_node_data'
        if HiveBackup.mode != HIVE_MODE_TEST:
            subprocess.call(line, shell=True)
        RcloneTool.remove_rclone_config_file(drive_name)

    # ------------------ backup to google end ----------------------------

    # ------------------ backup to node start ----------------------------
    def __proc_hive_node_param(self):
        did, content, err = did_post_json_param_pre_proc(self.response, "backup_credential",
                                                         access_vault=VAULT_ACCESS_R)
        if err:
            return None, None, err
        host, backup_token, err = view.h_auth.backup_auth_request(content)
        if err:
            return None, None, self.response.response_err(UNAUTHORIZED, err)

        info = get_vault_backup_info(did)
        if info and info[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP:
            if info[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
                data = dict()
                data["vault_backup_state"] = info[VAULT_BACKUP_INFO_STATE]
                return None, None, self.response.response_ok(data)

        upsert_vault_backup_info(did, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, host, backup_token)

        data, err = self.get_backup_service(host + INTER_BACKUP_SERVICE_URL, backup_token)
        if err:
            return None, None, err

        backup_service = data["backup_service"]
        return did, backup_service, None

    def get_backup_service(self, url, backup_token):
        try:
            r = requests.get(url,
                             headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"start_internal_backup exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return None, self.response.response_err(BAD_REQUEST, "start node backup error")

        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                "start_internal_backup error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                    r.status_code))
            return None, self.response.response_err(r.status_code,
                                                    "start internal backup error. content:" + str(r.content))
        else:
            data = r.json()
            return data, None

    @staticmethod
    def save_to_hive_node_finish(did, url, backup_token, checksum_list):
        param = {
            "checksum_list": checksum_list
        }
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"internal_save_app_list exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return False

        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                "internal_save_app_list error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                    r.status_code) + " content:" + str(r.content))
            return False
        else:
            return True

    @staticmethod
    def restore_backup_finish(did, url, backup_token):
        param = {}
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(f"internal_restore_data exception:{str(e)}, did:{did} host:{url}")
            return False

        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(f"internal_restore_data error, did:{did} host:{url} error code {str(r.status_code)} content {str(r.content)}")
            return False
        else:
            data = r.json()
            checksum_list = data["checksum_list"]
            vault_path = get_vault_path(did)
            if not vault_path.exists():
                logging.getLogger("HiveBackup").error(
                    f"internal_restore_data error, did:{did} host:{url} vault not exist")
                return False

            restore_checksum_list = get_file_checksum_list(vault_path)
            for checksum in checksum_list:
                if checksum not in restore_checksum_list:
                    logging.getLogger("HiveBackup").error(
                        f"internal_restore_data error, did:{did} host:{url} vault restore check failed")
                    return False
            return True

    @staticmethod
    def __token_to_node_backup_data(access_token):
        alist = access_token.split(":")
        ftp_port = alist[0]
        user = alist[1]
        password = alist[2]
        return ftp_port, user, password

    @staticmethod
    def __data_to_node_backup_token(ftp_port, user, password):
        return f"{ftp_port}:{user}:{password}"

    @staticmethod
    def classify_save_files(saved_file_list, local_file_list, vault_folder):
        file_put_list = list()
        file_delete_list = list()
        file_patch_list = list()

        saved_file_dict = dict()
        for info in saved_file_list:
            name = info[1]
            checksum = info[0]
            saved_file_dict[name] = checksum

        # simple way of classifying
        for info in local_file_list:
            file_checksum = info[0]
            file_full_name = info[1]
            file_name = Path(info[1]).relative_to(vault_folder).as_posix()
            if file_name in saved_file_dict:
                save_checksum = saved_file_dict[file_name]
                if save_checksum != file_checksum:
                    file_patch_list.append([file_full_name, file_name])
                del saved_file_dict[file_name]
            else:
                file_put_list.append([file_full_name, file_name])

        for name in saved_file_dict.keys():
            file_delete_list.append(name)

        return file_put_list, file_patch_list, file_delete_list

    @staticmethod
    def put_files(file_put_list, host, token):
        if not file_put_list:
            return

        for info in file_put_list:
            src_file = info[0]
            dst_file = info[1]
            try:
                with open(src_file, "br") as f:
                    f.seek(0)
                    url = host + INTER_BACKUP_FILE_URL + '?file=' + dst_file
                    r = requests.put(url,
                                     data=f,
                                     headers={"Authorization": "token " + token})
            except Exception as e:
                logging.getLogger("HiveBackup").error(
                    f"__put_files exception:{str(e)}, host:{host}")
                continue
            if r.status_code != SUCCESS:
                logging.getLogger("HiveBackup").error(
                    f"__put_files err code:{r.status_code}, host:{host}")
                continue

    @staticmethod
    def get_unpatch_file_hash(file_name, host, token):
        get_file_hash_url = host + INTER_BACKUP_PATCH_HASH_URL + "?file=" + file_name
        try:
            r = requests.get(get_file_hash_url,
                             headers={"Authorization": "token " + token},
                             stream=True)
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"get_unpatch_file_hash exception:{str(e)}, host:{host}")
            return None
        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                f"get_unpatch_file_hash error code is:" + str(r.status_code))
            return None
        hashes = list()
        for line in r.iter_lines(chunk_size=CHUNK_SIZE):
            if not line:
                continue
            data = line.split(b',')
            h = (int(data[0]), data[1].decode("utf-8"))
            hashes.append(h)
        return hashes

    @staticmethod
    def patch_remote_file(src_file_name, dst_file_name, host, token):
        hashes = HiveBackup.get_unpatch_file_hash(dst_file_name, host, token)
        try:
            with open(src_file_name, "rb") as f:
                delta_list = rsyncdelta(f, hashes, blocksize=CHUNK_SIZE)
        except Exception as e:
            print(f"patch_remote_file get {src_file_name} delta exception:{str(e)}, host:{host}")
            logging.getLogger("HiveBackup").error(
                f"patch_remote_file get {src_file_name} delta exception:{str(e)}, host:{host}")
            return SERVER_OPEN_FILE_ERROR

        patch_delta_file = gene_temp_file_name()
        try:
            with open(patch_delta_file, "wb") as f:
                pickle.dump(delta_list, f)
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"patch_remote_file dump {dst_file_name} delta exception:{str(e)}, host:{host}")
            patch_delta_file.unlink()
            return SERVER_SAVE_FILE_ERROR

        post_delta_url = host + INTER_BACKUP_PATCH_DELTA_URL + "?file=" + dst_file_name
        try:
            with open(patch_delta_file.as_posix(), 'rb') as f:
                r = requests.post(post_delta_url,
                                  data=f,
                                  headers={"Authorization": "token " + token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"patch_remote_file post {dst_file_name} exception:{str(e)}, host:{host}")
            return SERVER_PATCH_FILE_ERROR
        if r.status_code != SUCCESS:
            return r.status_code
        patch_delta_file.unlink()
        return SUCCESS

    @staticmethod
    def patch_save_files(file_patch_list, host, token):
        if not file_patch_list:
            return

        for info in file_patch_list:
            src_file = info[0]
            dst_file = info[1]
            HiveBackup.patch_remote_file(src_file, dst_file, host, token)

    @staticmethod
    def delete_files(file_delete_list, host, token):
        if not file_delete_list:
            return

        for name in file_delete_list:
            try:
                r = requests.delete(host + INTER_BACKUP_FILE_URL + "?file=" + name,
                                    headers={"Authorization": "token " + token})
            except Exception as e:
                logging.getLogger("HiveBackup").error(
                    f"__delete_files exception:{str(e)}, host:{host}")
                continue
            if r.status_code != SUCCESS:
                logging.getLogger("HiveBackup").error(
                    f"__delete_files err code:{r.status_code}, host:{host}")
                continue

    @staticmethod
    def save_to_hive_node_start(vault_folder, did, host, backup_token):
        # 1. get backup file list (with checksum)
        try:
            r = requests.get(host + INTER_BACKUP_FILE_LIST_URL,
                             headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"save_to_hive_node_start INTER_BACKUP_FILE_LIST_URL exception:{str(e)}, did:{did} host:{host}")
            return False

        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                f"save_to_hive_node_start INTER_BACKUP_FILE_LIST_URL error, did:{did} host:{host} error code {str(r.status_code)}")
            return False

        # 2. classify dealing of files
        data = r.json()
        saved_file_list = data["backup_files"]
        file_md5_gene = deal_dir(vault_folder.as_posix(), get_file_md5_info)
        file_put_list, file_patch_list, file_delete_list = HiveBackup.classify_save_files(saved_file_list,
                                                                                          file_md5_gene,
                                                                                          vault_folder)

        # 3. deal local file to backup node
        HiveBackup.put_files(file_put_list, host, backup_token)
        HiveBackup.patch_save_files(file_patch_list, host, backup_token)
        HiveBackup.delete_files(file_delete_list, host, backup_token)

    @staticmethod
    def classify_restore_files(saved_file_list, local_file_list, vault_folder):
        file_get_list = list()
        file_patch_list = list()
        file_delete_list = list()

        if not saved_file_list:
            return file_get_list, file_patch_list, file_delete_list

        local_file_dict = dict()
        for info in local_file_list:
            file_full_name = info[1]
            checksum = info[0]
            local_file_dict[file_full_name] = checksum

        # simple way of classifying
        for info in saved_file_list:
            file_checksum = info[0]
            file_name = filter_path_root(info[1])
            file_full_name = (vault_folder / file_name).as_posix()
            if file_full_name in local_file_dict:
                save_checksum = local_file_dict[file_full_name]
                if save_checksum != file_checksum:
                    file_patch_list.append([file_name, file_full_name])
                del local_file_dict[file_full_name]
            else:
                file_get_list.append([file_name, file_full_name])

        for file_full_name in local_file_dict.keys():
            file_delete_list.append(file_full_name)

        return file_get_list, file_patch_list, file_delete_list

    @staticmethod
    def get_files(file_get_list, host, token):
        if not file_get_list:
            return

        for info in file_get_list:
            src_file = info[0]
            dst_file = Path(info[1])
            dst_file.resolve()
            temp_file = gene_temp_file_name()

            if not dst_file.parent.exists():
                if not create_full_path_dir(dst_file.parent):
                    logging.getLogger("HiveBackup").error(
                        f"__get_files error mkdir :{dst_file.parent.as_posix()}, host:{host}")
                    continue
            try:
                r = requests.get(host + INTER_BACKUP_FILE_URL + "?file=" + src_file,
                                 stream=True,
                                 headers={"Authorization": "token " + token})
                with open(temp_file, 'bw') as f:
                    f.seek(0)
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
            except Exception as e:
                logging.getLogger("HiveBackup").error(
                    f"__get_files exception:{str(e)}, host:{host}")
                temp_file.unlink()
                continue
            if r.status_code != SUCCESS:
                logging.getLogger("HiveBackup").error(f"__get_files err code:{r.status_code}, host:{host}")
                temp_file.unlink()
                continue

            if dst_file.exists():
                dst_file.unlink()
            shutil.move(temp_file.as_posix(), dst_file.as_posix())

    @staticmethod
    def patch_local_file(src_file_name, dst_file_name, host, token):
        full_dst_file_name = Path(dst_file_name).resolve()
        try:
            with open(full_dst_file_name, 'rb') as open_file:
                gene = gene_blockchecksums(open_file, blocksize=CHUNK_SIZE)
                hashes = ""
                for h in gene:
                    hashes += h
                r = requests.post(host + INTER_BACKUP_GENE_DELTA_URL + "?file=" + src_file_name,
                                  data=hashes,
                                  stream=True,
                                  headers={"content-type": "application/json",
                                           "Authorization": "token " + token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"__delete_files exception:{str(e)}, host:{host}")
            return INTERNAL_SERVER_ERROR
        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                f"__delete_files err code:{r.status_code}, host:{host}")
            return r.status_code

        patch_delta_file = gene_temp_file_name()
        with open(patch_delta_file, 'wb') as f:
            f.seek(0)
            for chunk in r.iter_content(CHUNK_SIZE):
                f.write(chunk)

        with open(patch_delta_file, 'rb') as f:
            delta_list = pickle.load(f)
        try:
            new_file = gene_temp_file_name()
            with open(full_dst_file_name, "br") as unpatched:
                with open(new_file, "bw") as save_to:
                    unpatched.seek(0)
                    patchstream(unpatched, save_to, delta_list)
            patch_delta_file.unlink()
            if full_dst_file_name.exists():
                full_dst_file_name.unlink()
            shutil.move(new_file.as_posix(), full_dst_file_name.as_posix())
        except Exception as e:
            logging.getLogger("HiveBackup").error(f"exception of post_file_patch_delta patch error is {str(e)}")
            return SERVER_PATCH_FILE_ERROR

        return SUCCESS

    @staticmethod
    def patch_restore_files(file_patch_list, host, token):
        if not file_patch_list:
            return

        for info in file_patch_list:
            src_file = info[0]
            dst_file = info[1]
            HiveBackup.patch_local_file(src_file, dst_file, host, token)

    @staticmethod
    def restore_from_hive_node_start(vault_folder, did, host, backup_token):
        # 1. get backup file list (with checksum)
        try:
            r = requests.get(host + INTER_BACKUP_FILE_LIST_URL,
                             headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logging.getLogger("HiveBackup").error(
                f"restore_from_hive_node_start INTER_BACKUP_FILE_LIST_URL exception:{str(e)}, did:{did} host:{host}")
            return False

        if r.status_code != SUCCESS:
            logging.getLogger("HiveBackup").error(
                f"restore_from_hive_node_start INTER_BACKUP_FILE_LIST_URL error, did:{did} host:{host} error code {str(r.status_code)}")
            return False

        # 2. classify dealing of files
        data = r.json()
        saved_file_list = data["backup_files"]
        local_file_gene = deal_dir(vault_folder.as_posix(), get_file_md5_info)

        # 2. classfiy local file list
        file_get_list, file_patch_list, file_delete_list = HiveBackup.classify_restore_files(saved_file_list,
                                                                                             local_file_gene,
                                                                                             vault_folder)

        # 3. deal backup node file to local
        HiveBackup.get_files(file_get_list, host, backup_token)
        HiveBackup.patch_restore_files(file_patch_list, host, backup_token)
        HiveBackup.delete_files(file_delete_list, host, backup_token)

    def save_to_hive_node(self):
        did, backup_service, err = self.__proc_hive_node_param()
        if err:
            return err

        use_storage = get_vault_used_storage(did)
        if use_storage > backup_service[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            return self.response.response_err(INSUFFICIENT_STORAGE,
                                              f"The backup hive node dose not enough space for backup")

        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.save_vault_data, (did,))
        return self.response.response_ok()

    def restore_from_hive_node(self):
        did, backup_service, err = self.__proc_hive_node_param()
        if err:
            return err

        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.restore_vault_data, (did,))
        return self.response.response_ok()

    def activate_to_vault(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return self.response.response_err(UNAUTHORIZED, "Backup backup_to_vault auth failed")

        vault_service = get_vault_service(did)
        if not vault_service:
            return self.response.response_err(BAD_REQUEST, f"There is not vault service of {did} to active")

        backup_service = get_vault_backup_service(did)
        if not backup_service:
            return self.response.response_err(BAD_REQUEST, f"There is not vault backup service of {did}")

        freeze_vault(did)
        delete_user_vault_data(did)
        copy_local_backup_to_vault(did)
        import_mongo_db(did)
        delete_mongo_db_export(did)
        unfreeze_vault(did)
        return self.response.response_ok()
