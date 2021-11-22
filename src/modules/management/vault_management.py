# -*- coding: utf-8 -*-

"""
The vault management for the vault owner.
"""
import logging

from src.modules.ipfs.ipfs_files import IpfsFiles
from src.modules.subscription.subscription import VaultSubscription
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.file_manager import fm
from src.utils.http_exception import ApplicationNotFoundException
from src.utils.http_response import hive_restful_response
from src.utils_v1.constants import VAULT_ACCESS_R, USER_DID, APP_ID, VAULT_ACCESS_WR


class VaultManagement:
    def __init__(self):
        self.subscription = VaultSubscription()
        self.files = IpfsFiles()

    @hive_restful_response
    def get_apps(self):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_R)
        apps = cli.get_all_user_apps(user_did)
        results = list(filter(lambda b: b is not None, map(lambda a: self.get_app_detail(a), apps)))
        if not results:
            raise ApplicationNotFoundException()
        return {"apps": results}

    @hive_restful_response
    def delete_apps(self, app_dids):
        user_did, _ = check_auth_and_vault(VAULT_ACCESS_WR)
        for app_did in app_dids:
            name = cli.get_user_database_name(user_did, app_did)
            if not cli.is_database_exists(name):
                continue
            logging.debug(f'start remove the application: {user_did}, {app_did}')
            files = fm.get_app_file_metadatas(user_did, app_did)
            for file in files:
                self.files.decrease_refcount_cid(file['cid'])
            cli.remove_database(user_did, app_did)

    def get_app_detail(self, app):
        name = cli.get_user_database_name(app[USER_DID], app[APP_ID])
        if not cli.is_database_exists(name):
            return None
        return {
            "user_did": app[USER_DID],
            "app_did": app[APP_ID],
            "database_name": name,
            "file_use_storage": fm.ipfs_get_app_file_usage(name),
            "db_use_storage": cli.get_database_size(name),
        }
