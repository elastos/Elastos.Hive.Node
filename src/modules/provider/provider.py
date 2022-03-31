# -*- coding: utf-8 -*-

"""
The node management for the node owner.
"""
import logging

import base58
from bson import ObjectId

from src import hive_setting
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import COL_IPFS_BACKUP_SERVER, USR_DID, COL_RECEIPTS, COL_RECEIPTS_ORDER_ID, \
    COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, \
    COL_RECEIPTS_PAID_DID, DID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth
from src.utils.http_exception import ForbiddenException, VaultNotFoundException, BackupNotFoundException, \
    ReceiptNotFoundException
from src.utils.http_response import hive_restful_response
from src.utils_v1.auth import get_verifiable_credential_info
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_USE_STORAGE


class Provider:
    def __init__(self):
        self.owner_did = Provider.get_verified_owner_did()
        logging.info(f'Owner DID: {self.owner_did}')
        self.subscription = VaultSubscription()
        self.backup_server = IpfsBackupServer()

    @staticmethod
    def get_verified_owner_did():
        try:
            credential = base58.b58decode(hive_setting.NODE_CREDENTIAL).decode('utf8')
        except:
            raise RuntimeError(f'get_verified_owner_did: invalid value of NODE_CREDENTIAL')
        info, err_msg = get_verifiable_credential_info(credential)
        if err_msg:
            raise RuntimeError(f'get_verified_owner_did: {err_msg}')
        return info['__issuer']

    @hive_restful_response
    def get_node_info(self):
        pass

    @hive_restful_response
    def get_vaults(self):
        self.check_auth_owner_id()
        vaults = cli.find_many_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {},
                                      create_on_absence=True, throw_exception=False)
        if not vaults:
            raise VaultNotFoundException()
        return {
            "vaults": list(map(lambda v: {
                "pricing_using": v[VAULT_SERVICE_PRICING_USING],
                "max_storage": v[VAULT_SERVICE_MAX_STORAGE],
                "file_use_storage": v[VAULT_SERVICE_FILE_USE_STORAGE],
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
                "pricing_using": b[VAULT_BACKUP_SERVICE_USING],
                "max_storage": b[VAULT_BACKUP_SERVICE_MAX_STORAGE],
                "use_storage": b[VAULT_BACKUP_SERVICE_USE_STORAGE],
                "user_did": b[USR_DID],
            }, backups))
        }

    @hive_restful_response
    def get_filled_orders(self):
        self.check_auth_owner_id()
        receipts = cli.find_many_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {},
                                        create_on_absence=True, throw_exception=False)
        if not receipts:
            raise ReceiptNotFoundException(msg='Payment not found.')
        return {"payments": list(map(lambda r: self.get_filled_order(r), receipts))}

    def check_auth_owner_id(self):
        user_did, _ = check_auth()
        if user_did != self.owner_did:
            raise ForbiddenException(msg='No permission for accessing node information.')

    def get_filled_order(self, receipt):
        order = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {'_id': ObjectId(receipt[COL_RECEIPTS_ORDER_ID])},
                                    create_on_absence=True, throw_exception=False)
        return {
            "order_id": receipt[COL_RECEIPTS_ORDER_ID],
            "receipt_id": receipt['_id'],
            # info: compatible because of the key for user_did update from 'did' to 'user_did'.
            "user_did": receipt[USR_DID] if USR_DID in receipt else receipt[DID],
            "subscription": order[COL_ORDERS_SUBSCRIPTION] if order else None,
            "pricing_name": order[COL_ORDERS_PRICING_NAME] if order else None,
            "ela_amount": order[COL_ORDERS_ELA_AMOUNT] if order else None,
            "ela_address": order[COL_ORDERS_ELA_ADDRESS] if order else None,
            "paid_did": receipt[COL_RECEIPTS_PAID_DID],
        }
