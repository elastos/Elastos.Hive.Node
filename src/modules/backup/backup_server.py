# -*- coding: utf-8 -*-
import json
import logging

from flask import g

from src.modules.backup.encryption import Encryption
from src.modules.files.local_file import LocalFile
from src.utils.consts import BKSERVER_REQ_STATE, BACKUP_REQUEST_STATE_PROCESS, BKSERVER_REQ_ACTION, \
    BACKUP_REQUEST_ACTION_BACKUP, BKSERVER_REQ_CID, BKSERVER_REQ_SHA256, BKSERVER_REQ_SIZE, \
    BKSERVER_REQ_STATE_MSG, BACKUP_REQUEST_STATE_FAILED, COL_IPFS_BACKUP_SERVER, USR_DID, BACKUP_REQUEST_STATE_SUCCESS, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_BACKUP_SERVICE_USE_STORAGE, VAULT_SERVICE_MAX_STORAGE, BKSERVER_REQ_PUBLIC_KEY
from src.utils.http_exception import BackupNotFoundException, AlreadyExistsException, BadRequestException, \
    InsufficientStorageException, NotImplementedException, VaultNotFoundException
from src.utils.payment_config import PaymentConfig
from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.backup.backup import BackupManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.backup.backup_client import BackupClient
from src.modules.backup.backup_executor import ExecutorBase, BackupServerExecutor
from src.modules.files.ipfs_client import IpfsClient
from src.modules.subscription.subscription import VaultSubscription
from src.modules.subscription.vault import VaultManager


class BackupServer:
    def __init__(self):
        self.vault = VaultSubscription()
        self.client = BackupClient()
        self.auth = Auth()
        self.mcli = MongodbClient()
        self.user_manager = UserManager()
        self.vault_manager = VaultManager()
        self.backup_manager = BackupManager()
        self.ipfs_client = IpfsClient()

    def promotion(self):
        """ This processing is just like restore the vault:

        1. check the vault MUST not exist.
        2. check the backup request and get the metadata.
        3. create the vault of the free plan.
        4. increase the reference count of the file cid.
        5. restore all user databases.
        """
        backup = self.backup_manager.get_backup(g.usr_did)

        try:
            self.vault_manager.get_vault(g.usr_did)
            raise AlreadyExistsException('The vault already exists.')
        except VaultNotFoundException as e:
            pass

        vault = self.vault_manager.create_vault(g.usr_did, PaymentConfig.get_vault_plan('Free'), is_upgraded=True)
        request_metadata = self.get_server_request_metadata(g.usr_did, backup, is_promotion=True,
                                                            vault_max_size=vault[VAULT_SERVICE_MAX_STORAGE])

        # INFO: if free vault can not hold the backup data, then let it go
        #       or user can not promote again anymore.

        self.client.restore_database_by_dump_files(request_metadata)
        ExecutorBase.handle_cids_in_local_ipfs(request_metadata, contain_databases=False, only_files_ref=True)
        ExecutorBase.update_vault_usage_by_metadata(g.usr_did, request_metadata)

    def internal_backup(self, cid, sha256, size, is_force, public_key):
        # check currently whether it is in progress.
        backup = self.backup_manager.get_backup(g.usr_did)
        if not is_force and backup.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException('Failed because backup is in processing.')

        # pin the request metadata to local ipfs node.
        self.ipfs_client.cid_pin(cid)

        # recode the request and run the executor.
        update = {
            BKSERVER_REQ_ACTION: BACKUP_REQUEST_ACTION_BACKUP,
            BKSERVER_REQ_STATE: BACKUP_REQUEST_STATE_PROCESS,
            BKSERVER_REQ_STATE_MSG: '50',  # start from 50%
            BKSERVER_REQ_CID: cid,
            BKSERVER_REQ_SHA256: sha256,
            BKSERVER_REQ_SIZE: size,
            BKSERVER_REQ_PUBLIC_KEY: public_key
        }
        self.backup_manager.update_backup(g.usr_did, update)
        BackupServerExecutor(g.usr_did, self, self.backup_manager.get_backup(g.usr_did)).start()

    def internal_backup_state(self):
        backup = self.backup_manager.get_backup(g.usr_did)
        return {
            'state': backup.get(BKSERVER_REQ_ACTION),  # None or backup
            'result': backup.get(BKSERVER_REQ_STATE),
            'message': backup.get(BKSERVER_REQ_STATE_MSG),
            'public_key': Encryption.get_service_did_public_key(True)
        }

    def internal_restore(self, public_key):
        backup = self.backup_manager.get_backup(g.usr_did)

        # BKSERVER_REQ_ACTION: None, means not backup called; 'backup', backup called, and can be three states.
        if not backup.get(BKSERVER_REQ_ACTION):
            raise BadRequestException('No backup data for restoring on backup node.')
        elif backup.get(BKSERVER_REQ_ACTION) != BACKUP_REQUEST_ACTION_BACKUP:
            raise BadRequestException(f'No backup data for restoring with invalid action "{backup.get(BKSERVER_REQ_ACTION)}" on backup node.')

        # if BKSERVER_REQ_ACTION is not None, it can be three states
        if backup.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException('Failed because backup is in processing..')
        elif backup.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_FAILED:
            raise BadRequestException('Cannot execute restore because last backup is failed.')
        elif backup.get(BKSERVER_REQ_STATE) != BACKUP_REQUEST_STATE_SUCCESS:
            raise BadRequestException(f'Cannot execute restore because unknown state "{backup.get(BKSERVER_REQ_STATE)}".')

        if not backup.get(BKSERVER_REQ_CID):
            raise BadRequestException(f'Cannot execute restore because invalid data cid "{backup.get(BKSERVER_REQ_CID)}".')

        # decrypt and encrypt the metadata.
        try:
            tmp_file = LocalFile.generate_tmp_file_path()
            self.ipfs_client.download_file(backup.get(BKSERVER_REQ_CID), tmp_file)

            plain_path = Encryption.decrypt_file_with_curve25519(tmp_file, backup.get(BKSERVER_REQ_PUBLIC_KEY), True)
            cipher_path = Encryption.encrypt_file_with_curve25519(plain_path, public_key, True)
            self.ipfs_client.upload_file(cipher_path)
            cipher_path.unlink()
            plain_path.unlink()
            tmp_file.unlink()
        except Exception as e:
            raise BadRequestException(f'Failed to prepare restore metadata on the backup node: {e}')

        # backup data is valid, go on
        return {
            'cid': backup.get(BKSERVER_REQ_CID),
            'sha256': backup.get(BKSERVER_REQ_SHA256),
            'size': backup.get(BKSERVER_REQ_SIZE),
            'public_key': Encryption.get_service_did_public_key(True)
        }

    # the flowing is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        self.backup_manager.update_backup(user_did, {BKSERVER_REQ_STATE: state, BKSERVER_REQ_STATE_MSG: msg})

    def get_server_request_metadata(self, user_did, req, is_promotion=False, vault_max_size=0):
        """ Get the request metadata for promotion or backup.

        :param user_did
        :param req
        :param is_promotion
        :param vault_max_size Only for promotion.
        """
        request_metadata = self.__get_verified_request_metadata(user_did, req)
        logging.info('[IpfsBackupServer] Success to get verified request metadata.')

        if is_promotion:
            if request_metadata['vault_size'] > vault_max_size:
                raise InsufficientStorageException('No enough space for promotion.')
        else:
            # for backup
            if request_metadata['backup_size'] > req[VAULT_BACKUP_SERVICE_MAX_STORAGE]:
                raise InsufficientStorageException('No enough space for backup on the backup node.')
        logging.info('[IpfsBackupServer] Success to check the verified request metadata.')

        return request_metadata

    def __get_verified_request_metadata(self, user_did, req):
        cid, sha256, size, public_key = req.get(BKSERVER_REQ_CID), req.get(BKSERVER_REQ_SHA256), req.get(BKSERVER_REQ_SIZE), req.get(BKSERVER_REQ_PUBLIC_KEY)

        tmp_file = LocalFile.generate_tmp_file_path()
        self.ipfs_client.download_file(cid, tmp_file, is_proxy=True, sha256=sha256, size=size)

        plain_path = Encryption.decrypt_file_with_curve25519(tmp_file, public_key, True)
        tmp_file.unlink()

        with open(plain_path, 'r') as f:
            metadata = json.load(f)
        plain_path.unlink()
        return metadata

    # ipfs-subscription

    def subscribe(self):
        try:
            backup = self.backup_manager.get_backup(g.usr_did)
            if backup:
                raise AlreadyExistsException('The backup service is already subscribed.')
        except BackupNotFoundException as e:
            pass

        new_backup = self.backup_manager.create_backup(g.usr_did, PaymentConfig.get_free_backup_plan())
        return self.__get_backup_info(new_backup)

    def unsubscribe(self):
        backup = self.backup_manager.get_backup(g.usr_did)
        if backup.get(BKSERVER_REQ_STATE) == BACKUP_REQUEST_STATE_PROCESS:
            raise BadRequestException(f"The '{backup.get(BKSERVER_REQ_ACTION)}' is in process.")

        # INFO: maybe use has a vault.
        # self.user_manager.remove_user(g.usr_did)
        self.remove_backup_by_did(g.usr_did, backup)

    def remove_backup_by_did(self, user_did, doc):
        """ Remove all data belongs to the backup of the user. """
        logging.debug(f'start remove the backup of the user {user_did}, _id, {str(doc["_id"])}')
        if doc.get(BKSERVER_REQ_CID):
            request_metadata = self.__get_verified_request_metadata(user_did, doc)
            ExecutorBase.handle_cids_in_local_ipfs(request_metadata, root_cid=doc.get(BKSERVER_REQ_CID), is_unpin=True)

        self.backup_manager.remove_backup(user_did)

    def get_info(self):
        return self.__get_backup_info(self.backup_manager.get_backup(g.usr_did))

    def activate(self):
        raise NotImplementedException()

    def deactivate(self):
        raise NotImplementedException()

    def __get_backup_info(self, doc):
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
        self.backup_manager.update_backup(user_did, {VAULT_BACKUP_SERVICE_USE_STORAGE: size})

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
