# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from hive.util.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR
from src.modules.backup.backup_server import BackupClient
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.http_response import hive_restful_response, NotImplementedException
from src.view.auth import auth


class Backup:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting
        self.backup_client = BackupClient(hive_setting)

    @hive_restful_response
    def get_state(self):
        pass

    @hive_restful_response
    def backup(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = auth.get_backup_credential_info(credential)
        self.backup_client.check_backup_status(did)
        backup_service_info, access_token = self.backup_client.get_backup_service_info(credential, credential_info)
        self.backup_client.execute_backup(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def restore(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        credential_info = auth.get_backup_credential_info(credential)
        self.backup_client.check_backup_status(did)
        backup_service_info, access_token = self.backup_client.get_backup_service_info(credential, credential_info)
        self.backup_client.execute_restore(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()
