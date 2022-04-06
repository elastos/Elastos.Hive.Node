# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src.utils_v1.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR
from src.modules.auth.auth import Auth
from src.modules.deprecated.backup.backup_server import BackupClient
from src.utils.did_auth import check_auth_and_vault
from src.utils.http_exception import NotImplementedException
from src.utils.http_response import hive_restful_response


class Backup:
    def __init__(self, is_ipfs=False):
        self.client = BackupClient(is_ipfs)
        self.auth = Auth()
        self.is_ipfs = is_ipfs

    @hive_restful_response
    def get_state(self):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        return self.client.get_state(user_did)

    @hive_restful_response
    def backup(self, credential):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.client.check_backup_status(user_did)
        self.client.execute_backup(user_did, credential_info, self.client.get_access_token(credential, credential_info))

    @hive_restful_response
    def restore(self, credential):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        credential_info = self.auth.get_backup_credential_info(credential)
        self.client.check_backup_status(user_did, True)
        self.client.execute_restore(user_did, credential_info,
                                    self.client.get_access_token(credential, credential_info))

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()
