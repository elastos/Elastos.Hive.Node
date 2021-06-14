# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from hive.util.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR
from src.modules.backup.backup_server import BackupClient, BackupServer
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.http_response import hive_restful_response, NotImplementedException
from src.view.auth import auth


class Backup:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting
        self.client = BackupClient(hive_setting)
        self.server = BackupServer()

    @hive_restful_response
    def get_state(self):
        pass

    @hive_restful_response
    def backup(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = auth.get_backup_credential_info(credential)
        self.client.check_backup_status(did)
        backup_service_info, access_token = self.client.get_backup_service_info(credential, credential_info)
        self.client.execute_backup(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def restore(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        credential_info = auth.get_backup_credential_info(credential)
        self.client.check_backup_status(did)
        backup_service_info, access_token = self.client.get_backup_service_info(credential, credential_info)
        self.client.execute_restore(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()

    @hive_restful_response
    def backup_service(self):
        self.server.get_backup_service()

    @hive_restful_response
    def backup_finish(self, checksum_list):
        self.server.backup_finish(checksum_list)

    @hive_restful_response
    def backup_files(self):
        self.server.backup_files()

    @hive_restful_response
    def backup_get_file(self, file_name):
        self.server.backup_get_file(file_name)

    @hive_restful_response
    def backup_upload_file(self, file_name):
        self.server.backup_upload_file(file_name)

    @hive_restful_response
    def backup_delete_file(self, file_name):
        self.server.backup_delete_file(file_name)

    @hive_restful_response
    def backup_get_file_hash(self, file_name):
        self.server.backup_get_file_hash(file_name)

    @hive_restful_response
    def backup_patch_file(self, file_name):
        self.server.backup_patch_file(file_name)

    @hive_restful_response
    def restore_finish(self):
        self.server.restore_finish()
