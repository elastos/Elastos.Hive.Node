import _thread
import json
import logging
import pathlib
import subprocess

import requests
from pathlib import Path

from hive.main import view
from hive.settings import hive_setting
from hive.util.auth import did_auth
from hive.util.common import did_tail_part, create_full_path_dir, get_host
from hive.util.constants import APP_ID, VAULT_ACCESS_R, HIVE_MODE_TEST, HIVE_MODE_DEV, INTER_BACKUP_FTP_START_URL, \
    VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, INTER_BACKUP_FTP_END_URL, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_SERVICE_MAX_STORAGE, VAULT_BACKUP_INFO_FTP, VAULT_BACKUP_SERVICE_DATA, \
    INTER_BACKUP_SAVE_URL, VAULT_BACKUP_SERVICE_FTP
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, import_mongo_db, delete_mongo_db_export
from hive.util.error_code import BAD_REQUEST, UNAUTHORIZED
from hive.util.ftp_tool import FtpServer
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, get_vault_backup_path, \
    get_backup_used_storage, less_than_max_storage, gene_vault_backup_ftp_record, get_vault_backup_relative_path, \
    get_vault_backup_ftp_record, remove_vault_backup_ftp_record, import_files_from_backup, import_mongo_db_from_backup, \
    update_vault_backup_service_item
from hive.util.payment.vault_service_manage import get_vault_service, get_vault_used_storage, \
    update_vault_service_state, VAULT_SERVICE_STATE_FREEZE, freeze_vault, delete_user_vault, unfreeze_vault
from hive.util.vault_backup_info import *
from hive.util.rclone_tool import RcloneTool
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, did_post_json_param_pre_proc

logger = logging.getLogger("HiveBackup")


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
        if mode != HIVE_MODE_TEST:
            print("hive_setting.BACKUP_VAULTS_BASE_DIR:" + hive_setting.BACKUP_VAULTS_BASE_DIR)
            self.backup_ftp = FtpServer(hive_setting.BACKUP_VAULTS_BASE_DIR, hive_setting.BACKUP_FTP_PORT)
            self.backup_ftp.max_cons = 256
            self.backup_ftp.max_cons_per_ip = 10
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
    def restore_vault_data(did):
        info = get_vault_backup_info(did)
        if not info:
            return None
        update_vault_backup_state(did, VAULT_BACKUP_STATE_RESTORE, VAULT_BACKUP_MSG_SUCCESS)
        did_folder = HiveBackup.get_did_vault_path(did)
        if not did_folder.exists():
            create_full_path_dir(did_folder)

        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__restore_google_drive(did_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            HiveBackup.__restore_hive_node(did_folder, info[VAULT_BACKUP_INFO_FTP], did,
                                           info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_TOKEN])
        else:
            logger.error("restore_vault_data not support backup type:" + info[VAULT_BACKUP_INFO_TYPE])

        HiveBackup.import_did_mongodb_data(did)
        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.delete_did_mongodb_export_data(did)
        return info

    @staticmethod
    def save_vault_data(did):
        info = get_vault_backup_info(did)
        if not info:
            return None
        update_vault_backup_state(did, VAULT_BACKUP_STATE_BACKUP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.export_did_mongodb_data(did)
        did_folder = HiveBackup.get_did_vault_path(did)

        if info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE:
            HiveBackup.__save_google_drive(did_folder, info[VAULT_BACKUP_INFO_DRIVE])
        elif info[VAULT_BACKUP_INFO_TYPE] == VAULT_BACKUP_INFO_TYPE_HIVE_NODE:
            HiveBackup.__save_hive_node(did_folder, info[VAULT_BACKUP_INFO_FTP], did,
                                        info[VAULT_BACKUP_INFO_DRIVE], info[VAULT_BACKUP_INFO_TOKEN])
            HiveBackup.internal_save_app_list(did, info[VAULT_BACKUP_INFO_DRIVE] + INTER_BACKUP_SAVE_URL,
                                              info[VAULT_BACKUP_INFO_TOKEN])
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
            data = {"hive_backup_state": info[VAULT_BACKUP_INFO_STATE]}
        else:
            data = {"hive_backup_state": VAULT_BACKUP_STATE_STOP}
        return self.response.response_ok(data)

    @staticmethod
    def gene_did_google_drive_name(did):
        drive = "gdrive_%s" % did_tail_part(did)
        return drive

    @staticmethod
    def get_did_vault_path(did):
        path = pathlib.Path(hive_setting.VAULTS_BASE_DIR)
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
    def __proc_hive_node_param(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "backup_credential")
        if err:
            return None, None, None, err
        host, backup_token, err = view.h_auth.backup_auth_request(content)
        if err:
            return None, None, None, self.response.response_err(UNAUTHORIZED, err)

        info = get_vault_backup_info(did)
        if info and info[VAULT_BACKUP_INFO_STATE] != VAULT_BACKUP_STATE_STOP:
            if info[VAULT_BACKUP_INFO_TIME] < (datetime.utcnow().timestamp() - 60 * 60 * 24):
                data = dict()
                data["vault_backup_state"] = info[VAULT_BACKUP_INFO_STATE]
                return None, None, None, self.response.response_ok(data)

        upsert_vault_backup_info(did, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, host, backup_token)

        data, err = self.start_internal_ftp(host + INTER_BACKUP_FTP_START_URL, backup_token)
        if err:
            return None, None, None, err

        backup_service = data["backup_service"]
        access_token = data["token"]
        update_vault_backup_info_item(did, VAULT_BACKUP_INFO_FTP, access_token)
        return did, access_token, backup_service, None

    def start_internal_ftp(self, url, backup_token):
        param = {}
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logger.error(f"start_internal_backup exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return None, self.response.response_err(BAD_REQUEST, "start node backup error")

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
    def stop_internal_ftp(did, url, backup_token):
        param = {}
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
    def internal_save_app_list(did, url, backup_token):
        app_id_list = list()
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            app_id_list.append(did_info[APP_ID])

        param = {
            "app_id_list": app_id_list
        }
        try:
            r = requests.post(url,
                              json=param,
                              headers={"Content-Type": "application/json", "Authorization": "token " + backup_token})
        except Exception as e:
            logger.error(f"internal_save_app_list exception:{str(e)}, host:{url} backup_token:{backup_token}")
            return

        if r.status_code != 200:
            ret = r.json()
            if not ret["_error"]:
                logger.error(
                    "internal_save_app_list error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " content:" + str(r.content)))
            else:
                logger.error(
                    "internal_save_app_list error, host:" + url + " backup_token:" + backup_token + "error code:" + str(
                        r.status_code + " message:" + ret["_error"]["message"]))

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
    def __get_rclone_obscure(password):
        obj = subprocess.Popen(["rclone", "obscure", password],
                               stdout=subprocess.PIPE,
                               universal_newlines=True,
                               encoding="utf-8"
                               )
        encode_password = obj.stdout.read()
        obj.wait()
        obj.stdout.close()
        return encode_password.strip("\n")

    @staticmethod
    def __save_hive_node(did_folder, access_token, did, host, backup_token):
        ftp_port, user, password = HiveBackup.__token_to_node_backup_data(access_token)
        if HiveBackup.mode != HIVE_MODE_TEST:
            encode_password = HiveBackup.__get_rclone_obscure(password)
            ftp_host = get_host(host)
            line = f"rclone sync {did_folder.as_posix()} :ftp: --ftp-host={ftp_host} --ftp-port={ftp_port} --ftp-user={user} --ftp-pass={encode_password}"
            subprocess.call(line, shell=True)
        HiveBackup.stop_internal_ftp(did, host + INTER_BACKUP_FTP_END_URL, backup_token)

    @staticmethod
    def __restore_hive_node(did_folder, access_token, did, host, backup_token):
        ftp_port, user, password = HiveBackup.__token_to_node_backup_data(access_token)
        if HiveBackup.mode != HIVE_MODE_TEST:
            encode_password = HiveBackup.__get_rclone_obscure(password)
            ftp_host = get_host(host)
            line = f"rclone sync :ftp: {did_folder.as_posix()} --ftp-host={ftp_host} --ftp-port={ftp_port} --ftp-user={user} --ftp-pass={encode_password}"
            subprocess.call(line, shell=True)
        HiveBackup.stop_internal_ftp(did, host + INTER_BACKUP_FTP_END_URL, backup_token)

    def save_to_hive_node(self):
        did, access_token, backup_service, err = self.__proc_hive_node_param()
        if err:
            return err

        use_storage = get_vault_used_storage(did)
        if use_storage > backup_service[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
            return self.response.response_err(402, f"The backup hive node dose not enough space for backup")

        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.save_vault_data, (did,))
        return self.response.response_ok()

    def restore_from_hive_node(self):
        did, access_token, backup_service, err = self.__proc_hive_node_param()
        if err:
            return err

        if HiveBackup.mode != HIVE_MODE_TEST:
            _thread.start_new_thread(HiveBackup.restore_vault_data, (did,))
        return self.response.response_ok()

    # ------------------ backup to node end ----------------------------
    def inter_backup_save(self):
        did, content, err = did_post_json_param_pre_proc(self.response, "app_id_list")
        if err:
            return self.response.response_err(UNAUTHORIZED, "Backup internal backup_communication_start auth failed")

        update_vault_backup_service_item(did, VAULT_BACKUP_SERVICE_DATA, content["app_id_list"])
        return self.response.response_ok()

    def inter_backup_ftp_start(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return self.response.response_err(UNAUTHORIZED, "Backup internal backup_communication_start auth failed")

        # check backup service exist
        info = get_vault_backup_service(did)
        if not info:
            return self.response.response_err(BAD_REQUEST, "There is no backup service of " + did)

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            create_full_path_dir(backup_path)

        # add user to backup ftp server
        user, passwd = gene_vault_backup_ftp_record(did)

        if self.mode != HIVE_MODE_TEST:
            self.backup_ftp.add_user(user, passwd, backup_path, 'elradfmwMT')

        del info["_id"]
        if VAULT_BACKUP_SERVICE_FTP in info:
            del info[VAULT_BACKUP_SERVICE_FTP]
        if VAULT_BACKUP_SERVICE_DATA in info:
            del info[VAULT_BACKUP_SERVICE_DATA]

        data = {"token": HiveBackup.__data_to_node_backup_token(hive_setting.BACKUP_FTP_PORT, user, passwd),
                "backup_service": info}
        return self.response.response_ok(data)

    def inter_backup_ftp_end(self):
        did, app_id = did_auth()
        if not did:
            return self.response.response_err(UNAUTHORIZED, "Backup internal backup_communication_end auth failed")
        user, passwd = get_vault_backup_ftp_record(did)
        if not user:
            return self.response.response_err(BAD_REQUEST, "There is not backup process for " + did)
        if self.mode != HIVE_MODE_TEST:
            self.backup_ftp.remove_user(user)
        remove_vault_backup_ftp_record(did)
        return self.response.response_ok()

    def backup_to_vault(self):
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
        delete_user_vault(did)

        app_id_list = backup_service[VAULT_BACKUP_SERVICE_DATA]
        for app_id in app_id_list:
            import_files_from_backup(did, app_id)
            import_mongo_db_from_backup(did, app_id)
        unfreeze_vault(did)
        return self.response.response_ok()
