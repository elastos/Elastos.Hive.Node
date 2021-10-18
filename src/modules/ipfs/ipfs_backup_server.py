# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from src.modules.ipfs.ipfs_backup_client import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_executor import ExecutorBase, BackupServerExecutor
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import BKSERVER_REQ_STATE, BACKUP_REQUEST_STATE_INPROGRESS, BKSERVER_REQ_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BKSERVER_REQ_CID, BKSERVER_REQ_SHA256, BKSERVER_REQ_SIZE, \
    BKSERVER_REQ_STATE_MSG, BACKUP_REQUEST_STATE_FAILED, COL_IPFS_BACKUP_SERVER, USR_DID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth2
from src.utils.file_manager import fm
from src.utils.http_exception import BackupNotFoundException, AlreadyExistsException, BadRequestException, \
    InsufficientStorageException, NotImplementedException
from src.utils.http_response import hive_restful_response
from src.utils_v1.auth import get_current_node_did_string
from src.utils_v1.constants import DID_INFO_DB_NAME, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_BACKUP_SERVICE_USE_STORAGE, VAULT_SERVICE_MAX_STORAGE
from src.utils_v1.payment.payment_config import PaymentConfig


class IpfsBackupServer:
    def __init__(self):
        self.vault = VaultSubscription()
        self.client = IpfsBackupClient()

    @hive_restful_response
    def promotion(self):
        """ This processing is just like restore the vault:
        1. check the vault MUST not exist.
        2. check the backup request and get the metadata.
        3. create the vault of the free plan.
        4. increase the reference count of the file cid.
        5. restore all user databases.
        """
        user_did, app_did, doc = self._check_auth_backup()
        self.vault.get_checked_vault(user_did, is_not_exist_raise=False)
        vault = self.vault.create_vault(user_did, self.vault.get_price_plan('vault', 'Free'), is_upgraded=True)
        request_metadata = self.get_server_request_metadata(user_did, doc, is_promotion=True,
                                                            vault_max_size=vault[VAULT_SERVICE_MAX_STORAGE])
        self.client.check_can_be_restore(user_did, request_metadata)
        ExecutorBase.pin_cids_to_local_ipfs(request_metadata,
                                            is_only_file=True,
                                            is_file_pin_to_ipfs=False)
        self.client.restore_database_by_dump_files(request_metadata)
        ExecutorBase.update_vault_usage_by_metadata(user_did, request_metadata)

    @hive_restful_response
    def internal_backup(self, cid, sha256, size, is_force):
        user_did, app_did, doc = self._check_auth_backup()
        if not is_force and doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_INPROGRESS:
            raise BadRequestException(msg='Failed because backup is in processing.')
        fm.ipfs_pin_cid(cid)
        update = {
            BKSERVER_REQ_ACTION: BACKUP_REQUEST_ACTION_BACKUP,
            BKSERVER_REQ_STATE: BACKUP_REQUEST_STATE_INPROGRESS,
            BKSERVER_REQ_STATE_MSG: None,
            BKSERVER_REQ_CID: cid,
            BKSERVER_REQ_SHA256: sha256,
            BKSERVER_REQ_SIZE: size
        }
        self.update_backup_request(user_did, update)
        BackupServerExecutor(user_did, self, self.find_backup_request(user_did, False)).start()

    @hive_restful_response
    def internal_backup_state(self):
        user_did, app_did, doc = self._check_auth_backup()
        return {
            'state': doc.get(BKSERVER_REQ_ACTION),
            'result': doc.get(BKSERVER_REQ_STATE),
            'message': doc.get(BKSERVER_REQ_STATE_MSG)
        }

    @hive_restful_response
    def internal_restore(self):
        user_did, app_did, doc = self._check_auth_backup()
        if doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_INPROGRESS:
            raise BadRequestException(msg='Failed because backup is in processing..')
        elif doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_FAILED:
            raise BadRequestException(msg='Cannot execute restore because last backup is failed.')
        return {
            'cid': doc.get(BKSERVER_REQ_CID),
            'sha256': doc.get(BKSERVER_REQ_SHA256),
            'size': doc.get(BKSERVER_REQ_SIZE),
        }

    # the flowing is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        self.update_backup_request(user_did, {BKSERVER_REQ_STATE: state, BKSERVER_REQ_STATE_MSG: msg})

    def get_server_request_metadata(self, user_did, req, is_promotion=False, vault_max_size=0):
        """ Get the request metadata for promotion or backup.
        :param vault_max_size Only for promotion.
        """
        request_metadata = self._get_verified_request_metadata(user_did, req)
        logging.info('[IpfsBackupServer] Success to get verified request metadata.')
        self._check_verified_request_metadata(request_metadata, req,
                                              is_promotion=is_promotion,
                                              vault_max_size=vault_max_size)
        logging.info('[IpfsBackupServer] Success to check the verified request metadata.')
        return request_metadata

    def _get_verified_request_metadata(self, user_did, req):
        cid, sha256, size = req.get(BKSERVER_REQ_CID), req.get(BKSERVER_REQ_SHA256), req.get(BKSERVER_REQ_SIZE)
        return fm.ipfs_download_file_content(cid, is_proxy=True, sha256=sha256, size=size)

    def _check_verified_request_metadata(self, request_metadata, req, is_promotion=False, vault_max_size=0):
        if is_promotion:
            if request_metadata['vault_size'] > vault_max_size:
                raise InsufficientStorageException(msg='No enough space for promotion.')
        else:
            if request_metadata['vault_package_size'] > req[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
                raise InsufficientStorageException(msg='No enough space for backup on the backup node.')

    # ipfs-subscription

    @hive_restful_response
    def subscribe(self):
        user_did, app_did, doc = self._check_auth_backup(is_raise=False)
        if doc:
            raise AlreadyExistsException('The backup service is already subscribed.')
        return self._get_vault_info(self._create_backup(user_did, PaymentConfig.get_free_backup_info()))

    @hive_restful_response
    def unsubscribe(self):
        user_did, _, doc = self._check_auth_backup(is_raise=False)
        if not doc:
            return

        if doc.get(BKSERVER_REQ_CID):
            # INFO: remove relating CIDs.
            fm.ipfs_unpin_cid(doc.get(BKSERVER_REQ_CID))

        cli.delete_one_origin(DID_INFO_DB_NAME,
                              COL_IPFS_BACKUP_SERVER,
                              {USR_DID: user_did},
                              is_check_exist=False)

    @hive_restful_response
    def get_info(self):
        _, _, doc = self._check_auth_backup()
        return self._get_vault_info(doc)

    @hive_restful_response
    def activate(self):
        raise NotImplementedException()

    @hive_restful_response
    def deactivate(self):
        raise NotImplementedException()

    def _check_auth_backup(self, is_raise=True):
        user_did, app_did = check_auth2()
        return user_did, app_did, self.find_backup_request(user_did, is_raise=is_raise)

    def _create_backup(self, user_did, price_plan):
        now = datetime.utcnow().timestamp()
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {USR_DID: user_did,
               VAULT_BACKUP_SERVICE_USING: price_plan['name'],
               VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1024 * 1024,
               VAULT_BACKUP_SERVICE_USE_STORAGE: 0,
               VAULT_BACKUP_SERVICE_START_TIME: now,
               VAULT_BACKUP_SERVICE_END_TIME: end_time
               }
        cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, doc, create_on_absence=True, is_extra=True)
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

    def update_storage_usage(self, user_did, size):
        self.update_backup_request(user_did, {VAULT_BACKUP_SERVICE_USE_STORAGE: size})

    def update_backup_request(self, user_did, update):
        col_filter = {USR_DID: user_did}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, col_filter, {'$set': update}, is_extra=True)

    def find_backup_request(self, user_did, is_raise=True):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, {USR_DID: user_did},
                                  create_on_absence=True, throw_exception=False)
        if is_raise and not doc:
            raise BackupNotFoundException()
        return doc

    def retry_backup_request(self, user_did):
        req = self.find_backup_request(user_did, is_raise=False)
        if not req or req.get(BKSERVER_REQ_STATE) != BACKUP_REQUEST_STATE_INPROGRESS:
            return
        logging.info(f"[IpfsBackupServer] Found uncompleted request({req.get(USR_DID)}), retry.")
        BackupServerExecutor(user_did, self, req, start_delay=30).start()
