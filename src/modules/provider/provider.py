# -*- coding: utf-8 -*-

"""
The node management for the node owner.
"""
import json
import logging
import typing as t
from datetime import datetime

import base58
from flask import g

from src import hive_setting
from src.modules.backup.backup import BackupManager
from src.modules.subscription.vault import VaultManager
from src.utils.did.eladid_wrapper import Credential
from src.utils.consts import USR_DID, VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_USE_STORAGE
from src.utils.http_exception import ForbiddenException, ReceiptNotFoundException
from src.modules.payment.order import OrderManager


class Provider:
    def __init__(self):
        self.owner_did, self.credential = Provider.get_verified_owner_did()
        logging.info(f'Owner DID: {self.owner_did}')
        self.order_manager = OrderManager()
        self.vault_manager = VaultManager()
        self.backup_manager = BackupManager()

    @staticmethod
    def get_verified_owner_did():
        try:
            credential = base58.b58decode(bytes(hive_setting.NODE_CREDENTIAL, 'utf8')).decode('utf8')
        except:
            raise RuntimeError(f'get_verified_owner_did: invalid value of NODE_CREDENTIAL')
        info, err_msg = Provider._get_verifiable_credential_info(credential)
        if err_msg:
            raise RuntimeError(f'get_verified_owner_did: {err_msg}')
        return info['__issuer'], credential

    def get_vaults(self):
        """ Get all vaults in this node.

        :v2 API:
        """

        self.__check_auth_owner_id()

        def vault_mapper(v):
            result = {
                "pricing_using": v[VAULT_SERVICE_PRICING_USING],
                "max_storage": v.get_storage_quota(),
                "file_use_storage": v[VAULT_SERVICE_FILE_USE_STORAGE],
                "db_use_storage": v[VAULT_SERVICE_DB_USE_STORAGE],
                "user_did": v[VAULT_SERVICE_DID],
            }
            result.update(self.vault_manager.get_access_statistics(g.usr_did))
            return result

        vaults = self.vault_manager.get_all_vaults()
        return {
            "vaults": list(map(lambda v: vault_mapper(v), vaults))
        }

    def get_backups(self):
        """ Get all backup services in this node.

        :v2 API:
        """

        self.__check_auth_owner_id()

        backups = self.backup_manager.get_all_backups()
        return {
            "backups": list(map(lambda b: {
                "pricing_using": b[VAULT_BACKUP_SERVICE_USING],
                "max_storage": b[VAULT_BACKUP_SERVICE_MAX_STORAGE],
                "use_storage": b[VAULT_BACKUP_SERVICE_USE_STORAGE],
                "user_did": b[USR_DID],
            }, backups))
        }

    def get_filled_orders(self):
        self.__check_auth_owner_id()
        receipts = self.order_manager.get_receipts()
        if not receipts:
            raise ReceiptNotFoundException()
        return {
            'orders': [o.to_get_receipts() for o in receipts]
        }

    def __check_auth_owner_id(self):
        if g.usr_did != self.owner_did:
            raise ForbiddenException('No permission for accessing node information.')

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
