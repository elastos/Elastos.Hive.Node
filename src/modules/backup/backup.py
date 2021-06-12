# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from hive.util.constants import VAULT_ACCESS_R
from src.modules.backup.backup_server import BackupClient
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.http_response import hive_restful_response, NotImplementedException
from src.view.auth import auth


class Backup:
    def __init__(self):
        self.backup_client = BackupClient()

    @hive_restful_response
    def get_state(self):
        pass

    @hive_restful_response
    def backup(self, credential):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        credential_info = auth.get_backup_credential_info(credential)
        self.backup_client.check_backup_status(did)
        backup_service_info = self.backup_client.get_backup_service_info(credential, credential_info)
        self.backup_client.execute_backup(did, backup_service_info)

    @hive_restful_response
    def restore(self, source_node):
        pass

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()
