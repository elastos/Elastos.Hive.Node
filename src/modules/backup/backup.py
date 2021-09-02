# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src.utils_v1.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR
from src.modules.auth.auth import Auth
from src.modules.backup.backup_server import BackupClient
from src.utils.did_auth import check_auth_and_vault
from src.utils.http_exception import NotImplementedException
from src.utils.http_response import hive_restful_response


class Backup:
    def __init__(self, app=None, hive_setting=None, is_ipfs=False):
        self.hive_setting = hive_setting
        self.client = BackupClient(app, hive_setting, is_ipfs)
        self.auth = Auth(app, hive_setting)
        self.is_ipfs = is_ipfs

    @hive_restful_response
    def get_state(self):
        did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        return self.client.get_state(did)

    @hive_restful_response
    def backup(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.client.check_backup_status(did)
        # TODO: try to remove http access to the thread
        backup_service_info, access_token = self.client.get_backup_service_info(credential, credential_info)
        self.client.execute_backup(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def restore(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.client.check_backup_status(did, True)
        # TODO: try to remove http access to the thread
        backup_service_info, access_token = self.client.get_backup_service_info(credential, credential_info)
        self.client.execute_restore(did, credential_info, backup_service_info, access_token)

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()
