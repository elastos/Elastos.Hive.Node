import _thread
import logging
import os
import pathlib
import subprocess

import requests
from pathlib import Path

from hive.main import view
from hive.settings import VAULTS_BASE_DIR, BACKUP_VAULTS_BASE_DIR
from hive.util.auth import did_auth
from hive.util.common import did_tail_part, create_full_path_dir
from hive.util.constants import APP_ID, VAULT_ACCESS_R, HIVE_MODE_TEST, HIVE_MODE_DEV, INTER_BACKUP_START_URL, \
    VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, INTER_BACKUP_END_URL, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_SERVICE_MAX_STORAGE
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, import_mongo_db, delete_mongo_db_export
from hive.util.ftp_tool import FtpServer
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, get_vault_backup_path, \
    get_backup_used_storage, less_than_max_storage, gene_vault_backup_ftp_record, get_vault_backup_relative_path, \
    get_vault_backup_ftp_record, remove_vault_backup_ftp_record, import_files_from_backup, import_mongo_db_from_backup
from hive.util.payment.vault_service_manage import get_vault_service, get_vault_used_storage, \
    update_vault_service_state, VAULT_SERVICE_STATE_FREEZE, freeze_vault, delete_user_vault, unfreeze_vault
from hive.util.vault_backup_info import *
from hive.util.rclone_tool import RcloneTool
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc

logger = logging.getLogger("HiveBackup")

from hive.settings import BACKUP_FTP_PORT


class HiveBackup:
    mode = HIVE_MODE_DEV

    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveBackup")
        backup_path = Path(BACKUP_VAULTS_BASE_DIR)
        if not backup_path.exists:
            create_full_path_dir(backup_path)
        self.backup_ftp = FtpServer(BACKUP_VAULTS_BASE_DIR, BACKUP_FTP_PORT)

    def init_app(self, app, mode):
        self.app = app
        HiveBackup.mode = mode
        _thread.start_new_thread(self.backup_ftp.run, ())

    # ------------------ common start ----------------------------
    @staticmethod
    def import_did_mongodb_data(did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            import_mongo_db(did_info[DID], did_info[APP_ID])

    @staticmethod
    def export_did_mongodb_data(did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[DID], did_info[APP_ID])

    @staticmethod
    def delete_did_mongodb_export_data(did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            delete_mongo_db_export(did_info[DID], did_info[APP_ID])

    @staticmethod
    def restore_vault_data(did, arg):
        info = get_vault_backup_info(did)
        if not info:
            return
        update_vault_backup_state(did, VAULT_BACKUP_STATE_RESTORE, VAULT_BACKUP_MSG_SUCCESS)
        did_folder = HiveBackup.get_did_vault_path(did)
        if not did_folder.exists():
            create_full_path_dir(did_folder)

        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__restore_google_drive(did_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            HiveBackup.__restore_hive_node(did_folder, arg, did,
                                           info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_DATA])
        else:
            logger.error("restore_vault_data not support backup type:" + info[VAULT_BACKUP_INFO_TYPE])

        HiveBackup.import_did_mongodb_data(did)
        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.delete_did_mongodb_export_data(did)

    @staticmethod
    def save_vault_data(did, arg):
        info = get_vault_backup_info(did)
        if not info:
            return None
        update_vault_backup_state(did, VAULT_BACKUP_STATE_BACKUP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.export_did_mongodb_data(did)
        did_folder = HiveBackup.get_did_vault_path(did)

        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__save_google_drive(did_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            HiveBackup.__save_hive_node(did_folder, arg, did,
                                        info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_DATA])
        else:
            logger.error("restore_vault_data not support backup type:" + info[VAULT_BACKUP_INFO_TYPE])
            info = None

        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.delete_did_mongodb_export_data(did)
        return info

    # ------------------ common end ----------------------------

    # ------------------ backup to google start ----------------------------
    def __proc_google_drive_param(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response,
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
            if info[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow() - 60 * 60 * 24):
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
            return self.response.response_err(401, "auth failed")

        info = get_vault_backup_info(did)
        data = {"hive_backup_info": info}
        return self.response.response_ok(data)

    @staticmethod
    def gene_did_google_drive_name(did):
        drive = "gdrive_%s" % did_tail_part(did)
        return drive

    @staticmethod
    def get_did_vault_path(did):
        path = pathlib.Path(VAULTS_BASE_DIR)
        if path.is_absolute():
            path = path / did_tail_part(did)
        else:
            path = path.resolve() / did_tail_part(did)
        return path.resolve()

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
    def __proc_hive_node_param(self, immigrate=False):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "backup_credential")
        if err:
            return None, None, err
        host, backup_token, err = view.h_auth.backup_auth_request(content)
        if err:
            return None, None, self.response.response_err(401, err)

        info = get_vault_backup_info(did)
        if info and info[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP:
            if info[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow() - 60 * 60 * 24):
                data = dict()
                data["vault_backup_state"] = info[VAULT_BACKUP_INFO_STATE]
                return None, None, self.response.response_ok(data)

        upsert_vault_backup_info(did, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, host, backup_token)

        data, err = self.start_internal_backup(did, host + INTER_BACKUP_START_URL, backup_token, immigrate)
        if err:
            return None, None, err

        backup_max_storage = data["backup_max_storage"]
        use_storage = get_vault_used_storage(did)
        if use_storage > backup_max_storage:
            return None, None, self.response.response_err(402, f"The hive {host} dose not enough space for backup")

        if immigrate:
            service_max_storage = data["service_max_storage"]
            if use_storage > service_max_storage:
                return None, None, self.response.response_err(402,
                                                              f"The hive {host} dose not enough space to immigrate vault")

        return did, data["token"], None

    def start_internal_backup(self, did, url, backup_token, immigrate=False):
        if not immigrate:
            param = {
                "backup_did": did
            }
        else:
            param = {
                "backup_did": did,
                "immigrate": True
            }

        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logger.error(f"start_internal_backup exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return None, self.response.response_err(400, "start node backup error")

        if r.status_code != 200:
            ret = r.json()
            logger.error(
                "start_internal_backup error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                    r.status_code))
            if not ret["_error"]:
                return None, self.response.response_err(r.status_code,
                                                        "start internal backup error. content:" + str(r.content))
            else:
                return None, self.response.response_err(ret["_error"]["code"], ret["_error"]["message"])
        else:
            data = r.json()
            return data, None

    @staticmethod
    def stop_internal_backup(did, url, backup_token):
        param = {
            "backup_did": did
        }
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logger.error(f"stop_internal_backup exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return

        if r.status_code != 200:
            ret = r.json()
            if not ret["_error"]:
                logger.error(
                    "stop_internal_backup error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " content:" + str(r.content)))
            else:
                logger.error(
                    "stop_internal_backup error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " message:" + ret["_error"]["message"]))

    @staticmethod
    def internal_backup_to_vault(did, app_id_list, url, backup_token):
        param = {
            "backup_did": did,
            "app_id_list": app_id_list
        }
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logger.error(f"internal_backup_to_vault exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return

        if r.status_code != 200:
            ret = r.json()
            if not ret["_error"]:
                logger.error(
                    "internal_backup_to_vault error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " content:" + str(r.content)))
            else:
                logger.error(
                    "internal_backup_to_vault error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " message:" + ret["_error"]["message"]))

    @staticmethod
    def __token_to_node_backup_data(access_token):
        access_token.split(":")
        ftp_path = access_token[0]
        ftp_port = access_token[1]
        user = access_token[2]
        password = access_token[3]
        return ftp_path, ftp_port, user, password

    @staticmethod
    def __data_to_node_backup_token(ftp_path, ftp_port, user, password):
        return f"{ftp_path}:{ftp_port}:{user}:{password}"

    @staticmethod
    def __save_hive_node(did_folder, access_token, did, host, backup_token):
        ftp_path, ftp_port, user, password = HiveBackup.__token_to_node_backup_data(access_token)
        obj = subprocess.Popen(["rclone", "obscure", password],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True,
                               encoding="utf-8"
                               )
        encode_password = obj.stdout.read()
        obj.stdout.close()
        line = f"rclone sync {did_folder.as_posix()} :ftp:/{ftp_path} --ftp-host={host} --ftp-port={ftp_port} --ftp-user={user} --ftp-pass={encode_password}"
        if HiveBackup.mode != HIVE_MODE_TEST:
            subprocess.call(line, shell=True)
        HiveBackup.stop_internal_backup(did, host + INTER_BACKUP_END_URL, backup_token)

    @staticmethod
    def __restore_hive_node(did_folder, access_token, did, host, backup_token):
        ftp_path, ftp_port, user, password = HiveBackup.__token_to_node_backup_data(access_token)
        obj = subprocess.Popen(["rclone", "obscure", password],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True,
                               encoding="utf-8"
                               )
        encode_password = obj.stdout.read()
        obj.stdout.close()
        line = f"rclone sync :ftp:/{ftp_path} {did_folder.as_posix()} --ftp-host={host} --ftp-port={ftp_port} --ftp-user={user} --ftp-pass={encode_password}"
        if HiveBackup.mode != HIVE_MODE_TEST:
            subprocess.call(line, shell=True)
        HiveBackup.stop_internal_backup(did, host + INTER_BACKUP_END_URL, backup_token)

    def save_to_hive_node(self):
        did, access_token, err = self.__proc_hive_node_param()
        if not err:
            return err
        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.save_vault_data, (did, access_token))
        return self.response.response_ok()

    def restore_from_hive_node(self):
        did, access_token, err = self.__proc_hive_node_param()
        if not err:
            return err
        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.restore_vault_data, (did, access_token))
        return self.response.response_ok()

    def immigrate_node(self):
        did, access_token, err = self.__proc_hive_node_param(immigrate=True)
        if not err:
            return err
        if HiveBackup.mode != HIVE_MODE_TEST:
            freeze_vault(did)
            _thread.start_new_thread(HiveBackup.immigrate_vault_data, (did, access_token))
        return self.response.response_ok()

    @staticmethod
    def immigrate_vault_data(did, arg):
        info = HiveBackup.save_vault_data(did, arg)
        if info:
            app_id_list = list()
            did_info_list = get_all_did_info_by_did(did)
            for did_info in did_info_list:
                app_id_list.append(did_info[APP_ID])
            HiveBackup.internal_backup_to_vault(did, info[VAULT_BACKUP_INFO_DRIVE] + INTER_BACKUP_END_URL,
                                                info[VAULT_BACKUP_INFO_DATA])

    # ------------------ backup to node end ----------------------------

    def backup_communication_start(self):
        did, app_id, content, err = post_json_param_pre_proc()
        if err:
            return self.response.response_err(401, "Backup internal backup_communication_start auth failed")

        # check backup service exist
        info = get_vault_backup_service(did)
        if not info:
            return self.response.response_err(400, "There is no backup service of " + did)

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            create_full_path_dir(backup_path)
        else:
            # check whether enough room for backup
            get_backup_used_storage(did)
            if not less_than_max_storage(did):
                return self.response.response_err(400, "There is not enough backup room for " + did)

        # add user to backup ftp server
        user, passwd = gene_vault_backup_ftp_record(did)
        self.backup_ftp.add_user(user, passwd, backup_path, 'lradfmwMT')

        relative_path = get_vault_backup_relative_path(did)
        if ("immigrate" in content) and content["immigrate"]:
            vault_service = get_vault_service(did)
            if not vault_service:
                return self.response.response_err(400, f"There is not vault service of {did} to immigrate")
            data = {"token": HiveBackup.__data_to_node_backup_token(relative_path, BACKUP_FTP_PORT, user, passwd),
                    "backup_max_storage": info[VAULT_BACKUP_SERVICE_MAX_STORAGE],
                    "service_max_storage": vault_service[VAULT_SERVICE_MAX_STORAGE]
                    }
        else:
            data = {"token": HiveBackup.__data_to_node_backup_token(relative_path, BACKUP_FTP_PORT, user, passwd),
                    "backup_max_storage": info[VAULT_BACKUP_SERVICE_MAX_STORAGE]
                    }
        self.response.response_ok(data)

    def backup_communication_end(self):
        did, app_id = did_auth()
        if not did:
            return self.response.response_err(401, "Backup internal backup_communication_end auth failed")
        user, passwd = get_vault_backup_ftp_record(did)
        if not user:
            return self.response.response_err(400, "There is not backup process for " + did)
        remove_vault_backup_ftp_record(did)
        self.backup_ftp.remove_user(user)

    def backup_to_vault(self):
        did, app_id, content, err = post_json_param_pre_proc()
        if err:
            return self.response.response_err(401, "Backup internal backup_to_vault auth failed")
        freeze_vault(did)
        delete_user_vault(did)
        app_id_list = content["app_id_list"]
        for app_id in app_id_list:
            import_files_from_backup(did, app_id)
            import_mongo_db_from_backup(did, app_id)
        unfreeze_vault(did)
