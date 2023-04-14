# -*- coding: utf-8 -*-
import json
import logging

from flask import g

from src.modules.backup.encryption import Encryption
from src.modules.files.local_file import LocalFile
from src.utils.http_exception import BackupNotFoundException, AlreadyExistsException, BadRequestException, \
    InsufficientStorageException, NotImplementedException, VaultNotFoundException
from src.utils.payment_config import PaymentConfig
from src.modules.database.mongodb_collection import CollectionGenericField
from src.modules.backup.backup import Backup
from src.modules.backup.collection_backup import BackupRequestAction, BackupRequestState
from src.modules.database.mongodb_client import mcli
from src.modules.auth.auth import Auth
from src.modules.backup.backup_client import bc
from src.modules.backup.backup_executor import ExecutorBase, BackupServerExecutor
from src.modules.files.ipfs_client import IpfsClient
from src.modules.subscription.subscription import VaultSubscription


class BackupServer:
    def __init__(self):
        self.vault = VaultSubscription()
        self.client = bc
        self.auth = Auth()
        self.ipfs_client = IpfsClient()

    def promotion(self):
        """ This processing is just like restore the vault:

        1. check the vault MUST not exist.
        2. check the backup request and get the metadata.
        3. create the vault of the free plan.
        4. increase the reference count of the file cid.
        5. restore all user databases.
        """
        backup = mcli.get_col_backup().get_backup(g.usr_did)

        try:
            mcli.get_col_vault().get_vault(g.usr_did)
            raise AlreadyExistsException('The vault already exists.')
        except VaultNotFoundException as e:
            pass

        vault = mcli.get_col_vault().create_vault(g.usr_did, PaymentConfig.get_free_vault_plan(), is_upgraded=True)
        request_metadata = self.get_server_request_metadata(g.usr_did, backup, is_promotion=True,
                                                            vault_max_size=vault.get_storage_quota())

        # INFO: if free vault can not hold the backup data, then let it go
        #       or user can not promote again anymore.

        self.client.restore_database_by_dump_files(request_metadata)
        ExecutorBase.handle_cids_in_local_ipfs(request_metadata, contain_databases=False, only_files_ref=True)
        ExecutorBase.update_vault_usage_by_metadata(g.usr_did, request_metadata)

    def internal_backup(self, cid, sha256, size, is_force, public_key):
        # check currently whether it is in progress.
        backup = mcli.get_col_backup().get_backup(g.usr_did)
        if not is_force and backup.get_backup_request_state() == BackupRequestState.PROCESS:
            raise BadRequestException('Failed because backup is in processing.')

        # pin the request metadata to local ipfs node.
        self.ipfs_client.cid_pin(cid, size, sha256)

        mcli.get_col_backup().update_backup_request(BackupRequestAction.BACKUP, BackupRequestState.PROCESS, '50', cid, sha256, size, public_key)
        BackupServerExecutor(g.usr_did, self, mcli.get_col_backup().get_backup(g.usr_did)).start()

    def internal_backup_state(self):
        backup = mcli.get_col_backup().get_backup(g.usr_did)
        return {
            'state': backup.get_backup_request_action(),  # None or backup
            'result': backup.get_backup_request_state(),
            'message': backup.get_backup_request_state_msg(),
            'public_key': Encryption.get_service_did_public_key(True)
        }

    def internal_restore(self, public_key):
        backup = mcli.get_col_backup().get_backup(g.usr_did)

        # Action: None, means not backup called; 'backup', backup called, and can be three states.
        if not backup.get_backup_request_action():
            raise BadRequestException('No backup data for restoring on backup node.')
        elif backup.get_backup_request_action() != BackupRequestAction.BACKUP:
            raise BadRequestException(f'No backup data for restoring with invalid action "{backup.get_backup_request_action()}" on backup node.')

        # if state is not None, it can be three states
        if backup.get_backup_request_state() == BackupRequestState.PROCESS:
            raise BadRequestException('Failed because backup is in processing..')
        elif backup.get_backup_request_state() == BackupRequestState.FAILED:
            raise BadRequestException('Cannot execute restore because last backup is failed.')
        elif backup.get_backup_request_state() != BackupRequestState.SUCCESS:
            raise BadRequestException(f'Cannot execute restore because unknown state "{backup.get_backup_request_state()}".')

        if not backup.get_backup_request_cid():
            raise BadRequestException(f'Cannot execute restore because invalid data cid "{backup.get_backup_request_cid()}".')

        # decrypt and encrypt the metadata.
        try:
            tmp_file = LocalFile.generate_tmp_file_path()
            self.ipfs_client.download_file(backup.get_backup_request_cid(), tmp_file)

            plain_path = Encryption.decrypt_file_with_curve25519(tmp_file, backup.get_backup_request_public_key(), True)
            cipher_path = Encryption.encrypt_file_with_curve25519(plain_path, public_key, True)
            self.ipfs_client.upload_file(cipher_path)
            cipher_path.unlink()
            plain_path.unlink()
            tmp_file.unlink()
        except Exception as e:
            raise BadRequestException(f'Failed to prepare restore metadata on the backup node: {e}')

        # backup data is valid, go on
        return {
            'cid': backup.get_backup_request_cid(),
            'sha256': backup.get_backup_request_sha256(),
            'size': backup.get_backup_request_size(),
            'public_key': Encryption.get_service_did_public_key(True)
        }

    # the flowing is for the executors.

    def update_request_state(self, user_did, state, msg=None):
        col_backup = mcli.get_col_backup()
        col_backup.update_backup(user_did, {col_backup.REQUEST_STATE: state, col_backup.REQUEST_STATE_MSG: msg})

    def get_server_request_metadata(self, user_did, backup: Backup, is_promotion=False, vault_max_size=0):
        """ Get the request metadata for promotion or backup.

        :param user_did
        :param backup
        :param is_promotion
        :param vault_max_size Only for promotion.
        """
        request_metadata = self.__get_verified_request_metadata(user_did, backup)
        logging.info('[IpfsBackupServer] Success to get verified request metadata.')

        if is_promotion:
            if request_metadata['vault_size'] > vault_max_size:
                raise InsufficientStorageException('No enough space for promotion.')
        else:
            # for backup
            if request_metadata['backup_size'] > backup.get_storage_quota():
                raise InsufficientStorageException('No enough space for backup on the backup node.')
        logging.info('[IpfsBackupServer] Success to check the verified request metadata.')

        return request_metadata

    def __get_verified_request_metadata(self, user_did, req):
        cid, sha256, size, public_key = req.get_backup_request_cid(), req.get_backup_request_sha256(), req.get_backup_request_size(), req.get_backup_request_public_key()

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
            backup = mcli.get_col_backup().get_backup(g.usr_did)
            if backup:
                raise AlreadyExistsException('The backup service is already subscribed.')
        except BackupNotFoundException as e:
            pass

        new_backup = mcli.get_col_backup().create_backup(g.usr_did, PaymentConfig.get_free_backup_plan())
        return self.__get_backup_info(new_backup)

    def unsubscribe(self):
        backup = mcli.get_col_backup().get_backup(g.usr_did)
        if backup.get_backup_request_state() == BackupRequestState.PROCESS:
            raise BadRequestException(f"The '{backup.get_backup_request_state()}' is in process.")

        # INFO: maybe use has a vault.
        # mcli.get_col_application().remove_user(g.usr_did)
        self.remove_backup_by_did(g.usr_did, backup)

    def remove_backup_by_did(self, user_did, doc):
        """ Remove all data belongs to the backup of the user. """
        logging.debug(f'start remove the backup of the user {user_did}, _id, {str(doc["_id"])}')
        if doc.get_backup_request_cid():
            request_metadata = self.__get_verified_request_metadata(user_did, doc)
            ExecutorBase.handle_cids_in_local_ipfs(request_metadata, root_cid=doc.get_backup_request_cid(), is_unpin=True)

        mcli.get_col_backup().remove_backup(user_did)

    def get_info(self):
        return self.__get_backup_info(mcli.get_col_backup().get_backup(g.usr_did))

    def activate(self):
        raise NotImplementedException()

    def deactivate(self):
        raise NotImplementedException()

    def __get_backup_info(self, backup: Backup):
        return {
            'service_did': self.auth.get_did_string(),
            'pricing_plan': backup.get_plan_name(),
            'storage_quota': int(backup.get_storage_quota()),
            'storage_used': int(backup.get_storage_used()),
            'start_time': int(backup.get_started_time()),
            'end_time': int(backup.get_end_time()),
            'created': int(backup.get(CollectionGenericField.CREATED)),
            'updated': int(backup.get(CollectionGenericField.MODIFIED)),
        }

    def retry_backup_request(self):
        """ retry unfinished backup&restore action when node rebooted """
        backups: [Backup] = mcli.get_col_backup().get_all_backups()

        for backup in backups:
            if backup.get_backup_request_state() != BackupRequestState.PROCESS:
                return

            # only handle BackupRequestState.PROCESS ones.
            user_did = backup.get_user_did()
            logging.info(f"[IpfsBackupServer] Found uncompleted request({user_did}), retry.")
            BackupServerExecutor(user_did, self, backup, start_delay=30).start()

    def notify_progress(self, action, progress):
        """ Keep same method with client. """
        pass
