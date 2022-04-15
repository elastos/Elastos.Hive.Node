# -*- coding: utf-8 -*-

"""
The node management for the node owner.
"""
import json
import logging
import typing as t
from datetime import datetime

import base58
from bson import ObjectId
from flask import g

from src import hive_setting
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import COL_IPFS_BACKUP_SERVER, USR_DID, COL_RECEIPTS, COL_RECEIPTS_ORDER_ID, \
    COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, \
    COL_RECEIPTS_PAID_DID, DID
from src.utils.db_client import cli
from src.utils.http_exception import ForbiddenException, VaultNotFoundException, BackupNotFoundException, \
    ReceiptNotFoundException
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_USE_STORAGE
from src.utils.did.did_wrapper import Credential


class Provider:
    def __init__(self):
        self.owner_did, self.credential = Provider.get_verified_owner_did()
        logging.info(f'Owner DID: {self.owner_did}')
        self.subscription = VaultSubscription()
        self.backup_server = IpfsBackupServer()

    @staticmethod
    def get_verified_owner_did():
        try:
            credential = base58.b58decode(hive_setting.NODE_CREDENTIAL).decode('utf8')
        except:
            raise RuntimeError(f'get_verified_owner_did: invalid value of NODE_CREDENTIAL')
        info, err_msg = Provider._get_verifiable_credential_info(credential)
        if err_msg:
            raise RuntimeError(f'get_verified_owner_did: {err_msg}')
        return info['__issuer'], credential

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

    def get_filled_orders(self):
        self.check_auth_owner_id()
        receipts = cli.find_many_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {},
                                        create_on_absence=True, throw_exception=False)
        if not receipts:
            raise ReceiptNotFoundException(msg='Payment not found.')
        return {"payments": list(map(lambda r: self.get_filled_order(r), receipts))}

    def check_auth_owner_id(self):
        if g.usr_did != self.owner_did:
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

    @staticmethod
    def _get_verifiable_credential_info(vc_str: str) -> (t.Optional[dict], str):
        """
        Common version of the credential parsing logic.
        :return: all possible fields of the credential.
        """
        vc = Credential.from_json(vc_str)
        if not vc.is_valid():
            return None, 'The credential is invalid.'

        vc_json = json.loads(vc_str)
        if "credentialSubject" not in vc_json:
            return None, "The credentialSubject doesn't exist in credential."
        credential_subject = vc_json["credentialSubject"]
        if "id" not in credential_subject:
            return None, "The credentialSubject's id doesn't exist in credential."
        if "issuer" not in vc_json:
            return None, "The issuer doesn't exist in credential."

        credential_subject["__issuer"] = vc_json["issuer"]
        credential_subject["__expirationDate"] = vc.get_expiration_date()
        if credential_subject["__expirationDate"] == 0:
            return None, 'The expirationDate is invalid in credential'
        if int(datetime.now().timestamp()) > credential_subject["__expirationDate"]:
            return None, 'The expirationDate is expired in credential.'
        return credential_subject, None
