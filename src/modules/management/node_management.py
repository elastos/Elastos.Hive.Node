# -*- coding: utf-8 -*-

"""
The node management for the node owner.
"""
from bson import ObjectId

from src import hive_setting
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import COL_IPFS_BACKUP_SERVER, USR_DID, COL_RECEIPTS, COL_RECEIPTS_ORDER_ID, \
    COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, \
    COL_RECEIPTS_PAID_DID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth
from src.utils.file_manager import fm
from src.utils.http_exception import ForbiddenException, VaultNotFoundException, BackupNotFoundException, \
    ReceiptNotFoundException
from src.utils.http_response import hive_restful_response
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_USE_STORAGE


class NodeManagement:
    def __init__(self):
        self.owner_did = hive_setting.OWNER_DID
        assert self.owner_did, 'OWNER_DID must be setup.'
        self.subscription = VaultSubscription()
        self.backup_server = IpfsBackupServer()

    @hive_restful_response
    def get_vaults(self):
        self.check_auth_owner_id()
        vaults = cli.find_many_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {},
                                      create_on_absence=True, throw_exception=False)
        if not vaults:
            raise VaultNotFoundException()
        return {
            "vaults": list(map(lambda v: {
                # "id": str(v['_id']),
                "pricing_using": v[VAULT_SERVICE_PRICING_USING],
                "max_storage": v[VAULT_SERVICE_MAX_STORAGE],
                "file_use_storage": v[VAULT_SERVICE_FILE_USE_STORAGE],
                # "cache_use_storage": fm.ipfs_get_cache_size(v[VAULT_SERVICE_DID]),
                "db_use_storage": v[VAULT_SERVICE_DB_USE_STORAGE],
                "user_did": v[VAULT_SERVICE_DID],
            }, vaults))
        }

    @hive_restful_response
    def get_backups(self):
        self.check_auth_owner_id()
        backups = cli.find_many_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, {},
                                       create_on_absence=True, throw_exception=False)
        if not backups:
            raise BackupNotFoundException()
        return {
            "backups": list(map(lambda b: {
                # "id": str(b['_id']),
                "pricing_using": b[VAULT_BACKUP_SERVICE_USING],
                "max_storage": b[VAULT_BACKUP_SERVICE_MAX_STORAGE],
                "use_storage": b[VAULT_BACKUP_SERVICE_USE_STORAGE],
                "user_did": b[USR_DID],
            }, backups))
        }

    @hive_restful_response
    def get_users(self):
        self.check_auth_owner_id()
        return {"users": cli.get_all_user_dids()}

    @hive_restful_response
    def get_payments(self):
        self.check_auth_owner_id()
        receipts = cli.find_many_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {},
                                        create_on_absence=True, throw_exception=False)
        if not receipts:
            raise ReceiptNotFoundException(msg='Payment not found.')
        return {"payments": list(map(lambda r: self.get_payment_results(r), receipts))}

    @hive_restful_response
    def delete_vaults(self, user_dids):
        self.check_auth_owner_id()
        for user_did in user_dids:
            vault = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: user_did},
                                        create_on_absence=True, throw_exception=False)
            if vault:
                self.subscription.remove_vault_by_did(vault[VAULT_SERVICE_DID])

    @hive_restful_response
    def delete_backups(self, user_dids):
        self.check_auth_owner_id()
        for user_did in user_dids:
            backup = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, {USR_DID: user_did},
                                         create_on_absence=True, throw_exception=False)
            if backup:
                self.backup_server.remove_backup_by_did(backup[USR_DID], backup)

    def check_auth_owner_id(self):
        user_did, _ = check_auth()
        if user_did != self.owner_did:
            raise ForbiddenException(msg='No permission for accessing node information.')

    def get_payment_results(self, receipt):
        order = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {'_id': ObjectId(receipt[COL_RECEIPTS_ORDER_ID])},
                                    create_on_absence=True, throw_exception=False)
        return {
            "order_id": receipt[COL_RECEIPTS_ORDER_ID],
            "receipt_id": receipt['_id'],
            "user_did": receipt[USR_DID],
            "subscription": order[COL_ORDERS_SUBSCRIPTION] if order else None,
            "pricing_name": order[COL_ORDERS_PRICING_NAME] if order else None,
            "ela_amount": order[COL_ORDERS_ELA_AMOUNT] if order else None,
            "ela_address": order[COL_ORDERS_ELA_ADDRESS] if order else None,
            "paid_did": receipt[COL_RECEIPTS_PAID_DID],
        }
