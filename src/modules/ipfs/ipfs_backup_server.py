# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from flask import g

from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.ipfs.ipfs_backup_client import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_executor import ExecutorBase, BackupServerExecutor
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import BKSERVER_REQ_STATE, BACKUP_REQUEST_STATE_PROCESS, BKSERVER_REQ_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BKSERVER_REQ_CID, BKSERVER_REQ_SHA256, BKSERVER_REQ_SIZE, \
    BKSERVER_REQ_STATE_MSG, BACKUP_REQUEST_STATE_FAILED, COL_IPFS_BACKUP_SERVER, USR_DID, BACKUP_REQUEST_STATE_SUCCESS
from src.utils.db_client import cli
from src.utils.file_manager import fm
from src.utils.http_exception import BackupNotFoundException, AlreadyExistsException, BadRequestException, \
    InsufficientStorageException, NotImplementedException
from src.utils_v1.constants import DID_INFO_DB_NAME, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_BACKUP_SERVICE_USE_STORAGE, VAULT_SERVICE_MAX_STORAGE
from src.utils_v1.payment.payment_config import PaymentConfig


class IpfsBackupServer:
    def __init__(self):
        self.vault = VaultSubscription()
        self.client = IpfsBackupClient()
        self.auth = Auth()
        self.mcli = MongodbClient()
        self.user_manager = UserManager()

    def promotion(self):
        """ This processing is just like restore the vault:

        1. check the vault MUST not exist.
        2. check the backup request and get the metadata.
        3. create the vault of the free plan.
        4. increase the reference count of the file cid.
        5. restore all user databases.
        """
        doc = self.find_backup_request(g.usr_did, throw_exception=True)
        self.vault.get_checked_vault(g.usr_did, is_not_exist_raise=False)
        vault = self.vault.create_vault(g.usr_did, self.vault.get_price_plan('vault', 'Free'), is_upgraded=True)
        request_metadata = self.get_server_request_metadata(g.usr_did, doc, is_promotion=True,
                                                            vault_max_size=vault[VAULT_SERVICE_MAX_STORAGE])

        # INFO: if free vault can not hold the backup data, then let it go
        #       or user can not promote again anymore.
        # if request_metadata['vault_size'] > fm.get_vault_max_size(g.usr_did):
        #     raise InsufficientStorageException("No enough space to restore vault data")

        self.client.restore_database_by_dump_files(request_metadata)
        ExecutorBase.handle_cids_in_local_ipfs(request_metadata, contain_databases=False, only_files_ref=True)
        ExecutorBase.update_vault_usage_by_metadata(g.usr_did, request_metadata)

    def internal_backup(self, cid, sha256, size, is_force):
        doc = self.find_backup_request(g.usr_did, throw_exception=True)
        if not is_force and doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException('Failed because backup is in processing.')
        fm.ipfs_pin_cid(cid)
        update = {
            BKSERVER_REQ_ACTION: BACKUP_REQUEST_ACTION_BACKUP,
            BKSERVER_REQ_STATE: BACKUP_REQUEST_STATE_PROCESS,
            BKSERVER_REQ_STATE_MSG: '50',  # start from 50%
            BKSERVER_REQ_CID: cid,
            BKSERVER_REQ_SHA256: sha256,
            BKSERVER_REQ_SIZE: size
        }
        self.update_backup_request(g.usr_did, update)
        BackupServerExecutor(g.usr_did, self, self.find_backup_request(g.usr_did, False)).start()

    def internal_backup_state(self):
        doc = self.find_backup_request(g.usr_did, throw_exception=True)
        return {
            'state': doc.get(BKSERVER_REQ_ACTION),  # None or backup
            'result': doc.get(BKSERVER_REQ_STATE),
            'message': doc.get(BKSERVER_REQ_STATE_MSG)
        }

    def internal_restore(self):
        doc = self.find_backup_request(g.usr_did, throw_exception=True)

        # BKSERVER_REQ_ACTION: None, means not backup called; 'backup', backup called, and can be three states.
        if not doc.get(BKSERVER_REQ_ACTION):
            raise BadRequestException('No backup data for restoring on backup node.')
        elif doc.get(BKSERVER_REQ_ACTION) != BACKUP_REQUEST_ACTION_BACKUP:
            raise BadRequestException(f'No backup data for restoring with invalid action "{doc.get(BKSERVER_REQ_ACTION)}" on backup node.')

        # if BKSERVER_REQ_ACTION is not None, it can be three states
        if doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException('Failed because backup is in processing..')
        elif doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_FAILED:
            raise BadRequestException('Cannot execute restore because last backup is failed.')
        elif doc.get(BKSERVER_REQ_STATE) != BACKUP_REQUEST_STATE_SUCCESS:
            raise BadRequestException(f'Cannot execute restore because unknown state "{doc.get(BKSERVER_REQ_STATE)}".')

        if not doc.get(BKSERVER_REQ_CID):
            raise BadRequestException(f'Cannot execute restore because invalid data cid "{doc.get(BKSERVER_REQ_CID)}".')

        # backup data is valid, go on
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
                raise InsufficientStorageException('No enough space for promotion.')
        else:
            # for backup
            if request_metadata['backup_size'] > req[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
                raise InsufficientStorageException('No enough space for backup on the backup node.')

    # ipfs-subscription

    def subscribe(self):
        doc = self.find_backup_request(g.usr_did, throw_exception=False)
        if doc:
            raise AlreadyExistsException('The backup service is already subscribed.')
        return self._get_backup_info(self._create_backup(g.usr_did, PaymentConfig.get_free_backup_plan()))

    def unsubscribe(self):
        doc = self.find_backup_request(g.usr_did, throw_exception=True)
        if doc.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException(f"The '{doc.get(BKSERVER_REQ_ACTION)}' is in process.")

        # INFO: maybe use has a vault.
        # self.user_manager.remove_user(g.usr_did)
        self.remove_backup_by_did(g.usr_did, doc)

    def remove_backup_by_did(self, user_did, doc):
        """ Remove all data belongs to the backup of the user. """
        logging.debug(f'start remove the backup of the user {user_did}, _id, {str(doc["_id"])}')
        if doc.get(BKSERVER_REQ_CID):
            request_metadata = self._get_verified_request_metadata(user_did, doc)
            ExecutorBase.handle_cids_in_local_ipfs(request_metadata, root_cid=doc.get(BKSERVER_REQ_CID), is_unpin=True)

        cli.delete_one_origin(DID_INFO_DB_NAME,
                              COL_IPFS_BACKUP_SERVER,
                              {USR_DID: user_did},
                              is_check_exist=False)

    def get_info(self):
        return self._get_backup_info(self.find_backup_request(g.usr_did, throw_exception=True))

    def activate(self):
        raise NotImplementedException()

    def deactivate(self):
        raise NotImplementedException()

    def _create_backup(self, user_did, price_plan):
        now = int(datetime.now().timestamp())
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {USR_DID: user_did,
               VAULT_BACKUP_SERVICE_USING: price_plan['name'],
               VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1024 * 1024,
               VAULT_BACKUP_SERVICE_USE_STORAGE: 0,
               VAULT_BACKUP_SERVICE_START_TIME: now,
               VAULT_BACKUP_SERVICE_END_TIME: int(end_time)}
        cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, doc, create_on_absence=True, is_extra=True)
        return doc

    def _get_backup_info(self, doc):
        return {
            'service_did': self.auth.get_did_string(),
            'pricing_plan': doc[VAULT_BACKUP_SERVICE_USING],
            'storage_quota': int(doc[VAULT_BACKUP_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc.get(VAULT_BACKUP_SERVICE_USE_STORAGE, 0)),
            'start_time': int(doc[VAULT_BACKUP_SERVICE_START_TIME]),
            'end_time': int(doc[VAULT_BACKUP_SERVICE_END_TIME]),
            'created': int(doc.get('created')),
            'updated': int(doc.get('modified')),
        }

    def update_storage_usage(self, user_did, size):
        self.update_backup_request(user_did, {VAULT_BACKUP_SERVICE_USE_STORAGE: size})

    def update_backup_request(self, user_did, update):
        col_filter = {USR_DID: user_did}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, col_filter, {'$set': update}, is_extra=True)

    def find_backup_request(self, user_did, throw_exception=True):
        """ get the backup request information belonged to the user DID
        :param user_did: user DID
        :param throw_exception: throw BackupNotFoundException when True
        """
        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_BACKUP_SERVER, {USR_DID: user_did},
                                  create_on_absence=True, throw_exception=False)
        if throw_exception and not doc:
            raise BackupNotFoundException()
        return doc

    def retry_backup_request(self):
        """ retry unfinished backup&restore action when node rebooted """
        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)
        requests = col.find_many({})

        for req in requests:
            if req.get(BKSERVER_REQ_STATE) != BACKUP_REQUEST_STATE_PROCESS:
                return

            # only handle BACKUP_REQUEST_STATE_INPROGRESS ones.
            user_did = req[USR_DID]
            logging.info(f"[IpfsBackupServer] Found uncompleted request({user_did}), retry.")
            BackupServerExecutor(user_did, self, req, start_delay=30).start()
