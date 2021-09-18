# -*- coding: utf-8 -*-

from src.modules.ipfs.ipfs_backup import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_executor import ExecutorBase
from src.modules.subscription.subscription import VaultSubscription
from src.utils.did_auth import check_auth2
from src.utils.http_response import hive_restful_response


class IpfsBackupServer:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting
        self.vault = VaultSubscription(app, hive_setting)
        self.client = IpfsBackupClient(app, hive_setting)

    @hive_restful_response
    def promotion(self):
        did, app_did = check_auth2()
        self.vault.get_checked_vault(did, is_not_exist_raise=False)
        request_metadata = self.get_request_metadata(did)
        self.vault.create_vault(did, self.vault.get_price_plan('vault', 'Free'))
        self.client.check_can_be_restore(request_metadata)
        ExecutorBase.pin_cids_to_local_ipfs(request_metadata, is_only_file=True)
        self.client.restore_database_by_dump_files(request_metadata)

    @hive_restful_response
    def internal_backup(self):
        pass

    @hive_restful_response
    def internal_backup_state(self):
        pass

    @hive_restful_response
    def internal_restore(self):
        pass

    # the flowing is for the executors.

    def update_request_state(self, did, state, msg=None):
        pass

    def get_request_metadata(self, did):
        request_metadata = self._get_verified_request_metadata(did)
        self._check_can_be_backup(request_metadata)
        return request_metadata

    def _get_verified_request_metadata(self, did):
        return dict()

    def _check_can_be_backup(self, request_metadata):
        pass
