# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src import hive_setting
from src.modules.auth.auth import Auth
from src.modules.provider.provider import Provider


class About:
    def __init__(self):
        pass

    def get_version(self):
        """ This value comes from tag name and must be '***v<major>.<minor>.<patch>' or '<major>.<minor>.<patch>' """
        src = hive_setting.VERSION
        index = src.rfind('v')
        if index >= 0:
            src = src[index + 1:]
        parts = src.split('.')
        return {
            'major': int(parts[0]),
            'minor': int(parts[1]),
            'patch': int(parts[2]),
        }

    def get_commit_id(self):
        return {
            'commit_id': hive_setting.LAST_COMMIT
        }

    def get_node_info(self):
        from src.modules.auth.user import UserManager
        from src.modules.subscription.vault import VaultManager
        from src.modules.subscription.backup import BackupManager

        owner_did, credential = Provider.get_verified_owner_did()
        auth = Auth()
        return {
            "service_did": auth.did_str,
            "owner_did": owner_did,
            "ownership_presentation": auth.get_ownership_presentation(credential),
            "name": hive_setting.NODE_NAME,
            "email": hive_setting.NODE_EMAIL,
            "description": hive_setting.NODE_DESCRIPTION,
            "version": hive_setting.VERSION,
            "last_commit_id": hive_setting.LAST_COMMIT,
            "user_count": UserManager().get_user_count(),
            "vault_count": VaultManager().get_vault_count(),
            "backup_count": BackupManager().get_backup_count(),
        }
