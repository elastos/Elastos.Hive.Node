# -*- coding: utf-8 -*-
from datetime import datetime

from src.modules.ipfs.ipfs_backup import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_executor import ExecutorBase
from src.modules.subscription.subscription import VaultSubscription
from src.utils.db_client import cli
from src.utils.did_auth import check_auth2
from src.utils.http_exception import BackupNotFoundException, AlreadyExistsException
from src.utils.http_response import hive_restful_response
from src.utils_v1.auth import get_current_node_did_string
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, VAULT_BACKUP_SERVICE_DID, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_BACKUP_SERVICE_USE_STORAGE
from src.utils_v1.payment.payment_config import PaymentConfig


class IpfsBackupServer:
    def __init__(self, app=None, hive_setting=None):
        self.app = app
        self.hive_setting = hive_setting
        self.vault = VaultSubscription(app, hive_setting)
        self.client = IpfsBackupClient(app, hive_setting)

    @hive_restful_response
    def promotion(self):
        """ This processing is just like restore the vault:
        1. check the vault MUST not exist.
        2. check the backup request and get the metadata.
        3. create the vault of the free plan.
        4. increase the reference count of the file cid.
        5. restore all user databases.
        """
        did, app_did = check_auth2()
        self.vault.get_checked_vault(did, is_not_exist_raise=False)
        request_metadata = self.get_request_metadata(did)
        self.vault.create_vault(did, self.vault.get_price_plan('vault', 'Free'))
        self.client.check_can_be_restore(request_metadata)
        ExecutorBase.pin_cids_to_local_ipfs(request_metadata,
                                            is_only_file=True,
                                            is_file_pin_to_ipfs=False)
        self.client.restore_database_by_dump_files(request_metadata)

    @hive_restful_response
    def internal_backup(self, cid, sha256, size):
        # INFO: need refine backup subscription first.
        did, app_did, doc = self._check_auth_backup()
        # TODO:

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

    def _check_auth_backup(self, is_raise=True):
        did, app_did = check_auth2()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, {VAULT_BACKUP_SERVICE_DID: did},
                                  is_create=True, is_raise=False)
        if is_raise and not doc:
            raise BackupNotFoundException()
        return did, app_did, doc

    @hive_restful_response
    def subscribe(self):
        did, app_did, doc = self._check_auth_backup(is_raise=False, is_create=True)
        if doc:
            raise AlreadyExistsException('The backup vault is already subscribed.')
        return self._get_vault_info(self._create_backup(did, PaymentConfig.get_free_backup_info()))

    @hive_restful_response
    def unsubscribe(self):
        did, _, doc = self._check_auth_backup(is_raise=False)
        if not doc:
            return
        # TODO: remove backup request relating CIDs.
        cli.delete_one_origin(DID_INFO_DB_NAME,
                              VAULT_BACKUP_SERVICE_COL,
                              {VAULT_BACKUP_SERVICE_DID: did},
                              is_check_exist=False)

    @hive_restful_response
    def get_info(self):
        _, _, doc = self._check_auth_backup(is_create=True)
        return self._get_vault_info(doc)

    def _create_backup(self, did, price_plan):
        now = datetime.utcnow().timestamp()
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_BACKUP_SERVICE_DID: did,
               VAULT_BACKUP_SERVICE_USING: price_plan['name'],
               VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1024 * 1024,
               VAULT_BACKUP_SERVICE_START_TIME: now,
               VAULT_BACKUP_SERVICE_END_TIME: end_time
               }
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, doc, is_create=True, is_extra=True)
        return doc

    def _get_vault_info(self, doc):
        return {
            'pricing_plan': doc[VAULT_BACKUP_SERVICE_USING],
            'service_did': get_current_node_did_string(),
            'storage_quota': int(doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc.get(VAULT_BACKUP_SERVICE_USE_STORAGE, 0)),
            'created': doc.get('created'),
            'updated': doc.get('modified'),
        }
