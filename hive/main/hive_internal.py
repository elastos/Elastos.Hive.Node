import _thread
import json
import logging
import pathlib
import subprocess
import re
import sys

import requests
from pathlib import Path

from hive.main import view
from hive.util.auth import did_auth
from hive.util.common import did_tail_part, create_full_path_dir, get_host
from hive.util.common import did_tail_part, create_full_path_dir, get_host
from hive.util.constants import APP_ID, VAULT_ACCESS_R, HIVE_MODE_TEST, HIVE_MODE_DEV, INTER_BACKUP_FTP_START_URL, \
    VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE, VAULT_BACKUP_INFO_TYPE_HIVE_NODE, INTER_BACKUP_FTP_END_URL, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_SERVICE_MAX_STORAGE, VAULT_BACKUP_INFO_FTP, VAULT_BACKUP_SERVICE_APPS, \
    INTER_BACKUP_SAVE_FINISH_URL, VAULT_BACKUP_SERVICE_FTP, INTER_BACKUP_RESTORE_FINISH_URL
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, import_mongo_db, delete_mongo_db_export
from hive.util.error_code import BAD_REQUEST, UNAUTHORIZED, INSUFFICIENT_STORAGE, SUCCESS, NOT_FOUND, CHECKSUM_FAILED
from hive.util.ftp_tool import FtpServer
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, get_vault_backup_path, \
    gene_vault_backup_ftp_record, get_vault_backup_ftp_record, remove_vault_backup_ftp_record, import_files_from_backup, \
    import_mongo_db_from_backup, update_vault_backup_service_item, get_backup_used_storage
from hive.util.payment.vault_service_manage import get_vault_service, get_vault_used_storage, \
    update_vault_service_state, VAULT_SERVICE_STATE_FREEZE, freeze_vault, delete_user_vault, unfreeze_vault, \
    get_vault_path, delete_user_vault_data
from hive.util.vault_backup_info import *
from hive.util.rclone_tool import RcloneTool
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, did_post_json_param_pre_proc
from hive.settings import hive_setting


class HiveInternal:
    mode = HIVE_MODE_DEV

    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveInternal")
        self.backup_ftp = None

    def init_app(self, app, mode):
        backup_path = Path(hive_setting.BACKUP_VAULTS_BASE_DIR)
        if not backup_path.exists:
            create_full_path_dir(backup_path)
        self.app = app
        HiveInternal.mode = mode

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



    # ------------------ internal start ----------------------------
    def backup_save_finish(self):
        did, content, err = did_post_json_param_pre_proc(self.response, "app_id_list", "checksum_list")
        if err:
            return err

        update_vault_backup_service_item(did, VAULT_BACKUP_SERVICE_APPS, content["app_id_list"])

        get_backup_used_storage(did)

        checksum_list = content["checksum_list"]
        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            return self.response.response_err(NOT_FOUND, f"{did} backup vault not found")

        backup_checksum_list = HiveInternal.get_file_checksum_list(backup_path)
        for checksum in checksum_list:
            if checksum not in backup_checksum_list:
                return self.response.response_err(CHECKSUM_FAILED, f"{did} backup file checksum failed")

        return self.response.response_ok()

    def backup_restore_finish(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return err

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            return self.response.response_err(NOT_FOUND, f"{did} backup vault not found")

        backup_checksum_list = HiveInternal.get_file_checksum_list(backup_path)
        data = {"checksum_list": backup_checksum_list}
        return self.response.response_ok(data)

    def get_backup_service(self):
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

        del info["_id"]
        if VAULT_BACKUP_SERVICE_APPS in info:
            del info[VAULT_BACKUP_SERVICE_APPS]

        data = {"backup_service": info}
        return self.response.response_ok(data)


    def get_transfer_files(self):
        pass

    def upload_file(self):
        pass

    def move_file(self):
        pass

    def copy_file(self):
        pass

    def get_file_hash(self):
        pass

    def post_file_delta(self):
        pass
