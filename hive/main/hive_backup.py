import _thread
import pathlib
import subprocess

from hive.settings import VAULTS_BASE_DIR
from hive.util.common import did_tail_part, create_full_path_dir
from hive.util.constants import APP_ID, VAULT_ACCESS_R
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import export_mongo_db, import_mongo_db, delete_mongo_db_backup
from hive.util.vault_backup_info import *
from hive.util.rclone_tool import RcloneTool
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc


class HiveBackup:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveBackup")

    def init_app(self, app):
        self.app = app

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
            data = dict()
            data["vault_backup_state"] = info[VAULT_BACKUP_INFO_STATE]
            return None, None, self.response.response_ok(data)
        config_data = RcloneTool.get_config_data(content, did)
        drive_name = HiveBackup.gene_did_google_drive_name(did)

        RcloneTool.create_rclone_config_file(drive_name, config_data)
        if not info:
            add_vault_backup_info(did, drive_name)
        return did, drive_name, None

    def save_to_google_drive(self):
        did, drive_name, err = self.__proc_google_drive_param()
        if err:
            return err

        _thread.start_new_thread(HiveBackup.save_vault_data, (did, drive_name))

        return self.response.response_ok()

    def restore_from_google_drive(self):
        did, drive_name, err = self.__proc_google_drive_param()
        if err:
            return err

        _thread.start_new_thread(HiveBackup.restore_vault_data, (did, drive_name))

    def get_sync_google_drive_state(self):
        pass

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
            delete_mongo_db_backup(did_info[DID], did_info[APP_ID])

    @staticmethod
    def restore_vault_data(did, drive_name):
        update_vault_backup_state(did, VAULT_BACKUP_STATE_RESTORE, VAULT_BACKUP_MSG_SUCCESS)
        did_folder = HiveBackup.get_did_vault_path(did)
        if not did_folder.exists():
            create_full_path_dir(did_folder)
        line = 'rclone sync %s:elastos_hive_node_data %s' % (drive_name, did_folder.as_posix())
        subprocess.call(line, shell=True)
        HiveBackup.import_did_mongodb_data(did)
        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.delete_did_mongodb_export_data(did)
        RcloneTool.remove_rclone_config_file(drive_name)

    @staticmethod
    def save_vault_data(did, drive_name):
        update_vault_backup_state(did, VAULT_BACKUP_STATE_BACKUP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.export_did_mongodb_data(did)
        did_folder = HiveBackup.get_did_vault_path(did)
        line = 'rclone sync %s %s:elastos_hive_node_data' % (did_folder.as_posix(), drive_name)
        subprocess.call(line, shell=True)
        update_vault_backup_state(did, VAULT_BACKUP_STATE_STOP, VAULT_BACKUP_MSG_SUCCESS)
        HiveBackup.delete_did_mongodb_export_data(did)
        RcloneTool.remove_rclone_config_file(drive_name)
