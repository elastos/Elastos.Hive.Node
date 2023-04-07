from datetime import datetime

from src.utils.customize_dict import Dotdict
from src.utils.payment_config import PaymentConfig
from src.utils.http_exception import VaultFrozenException


class Vault(Dotdict):
    """ Represents a user vault """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_user_did(self):
        return self.did

    def get_storage_quota(self):
        # bytes, compatible with v1 (unit MB), v2 (unit Byte)
        return int(self.max_storage * 1024 * 1024 if self.max_storage < 1024 * 1024 else self.max_storage)

    def get_database_usage(self):
        return int(self.db_use_storage)

    def get_files_usage(self):
        return int(self.file_use_storage)

    def get_storage_gap(self):
        return int(self.get_storage_quota() - self.get_storage_usage())

    def get_storage_usage(self):
        return int(self.get_files_usage() + self.get_database_usage())

    def is_storage_full(self):
        return self.get_storage_gap() <= 0

    def check_storage_full(self):
        """ if storage is full, raise InsufficientStorageException """
        # TODO: temporary comment these because an issue vault full
        # if self.is_storage_full():
        #     raise InsufficientStorageException()
        return self

    def check_write_permission(self):
        """ if vault is freeze, raise VaultFrozenException """
        from src.modules.subscription.collection_vault import VaultState
        if self.state == VaultState.FROZE:
            raise VaultFrozenException('The vault can not be writen')
        return self

    def get_plan(self):
        return PaymentConfig.get_vault_plan(self.pricing_using)

    def get_plan_name(self):
        return self.pricing_using

    def is_expired(self):
        return 0 < self.end_time < datetime.now().timestamp()

    def get_started_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def get_modified_time(self):
        return self.modify_time

    def get_latest_access_time(self):
        from src.modules.subscription.collection_vault import CollectionVault
        return int(self.latest_access_time) if hasattr(self, CollectionVault.LATEST_ACCESS) and self.latest_access_time else -1
