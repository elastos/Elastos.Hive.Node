import shutil
from datetime import datetime

from src import hive_setting
from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient, Dotdict
from src.utils.consts import COL_IPFS_FILES
from src.utils.http_exception import InsufficientStorageException, VaultNotFoundException, CollectionNotFoundException, VaultFrozenException
from src.utils_v1.constants import VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_COL, \
    VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_MODIFY_TIME, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_STATE_FREEZE, VAULT_SERVICE_STATE, VAULT_SERVICE_STATE_RUNNING, VAULT_SERVICE_LATEST_ACCESS_TIME
from src.utils_v1.payment.payment_config import PaymentConfig


class Vault(Dotdict):
    """ Represents a user vault """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_storage_quota(self):
        # bytes, compatible with v1 (unit MB), v2 (unit Byte)
        return int(self.max_storage * 1024 * 1024 if self.max_storage < 1024 * 1024 else self.max_storage)

    def get_database_usage(self):
        return int(self.db_use_storage)

    def get_files_usage(self):
        return int(self.file_use_storage)

    def get_storage_gap(self):
        return int(self.get_storage_quota() - (self.file_use_storage + self.db_use_storage))

    def get_storage_usage(self):
        return int(self.file_use_storage + self.db_use_storage)

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
        if self.state == VAULT_SERVICE_STATE_FREEZE:
            raise VaultFrozenException('The vault can not be writen')
        return self

    def get_plan(self):
        return PaymentConfig.get_pricing_plan(self.pricing_using)

    def get_plan_name(self):
        return self.pricing_using

    def is_expired(self):
        return 0 < self.end_time < datetime.now().timestamp()

    def get_end_time(self):
        return self.end_time


class AppSpaceDetector:
    """ can only detect the database space size changes

    Files storage size changing can be checked by file size accurately.

    @deprecated
    """

    def __init__(self, user_did, app_did):
        self.user_did, self.app_did = user_did, app_did
        self.vault_manager = VaultManager()
        self.dbsize_before = self.vault_manager.get_user_database_size(user_did, app_did)

    def __enter__(self):
        return self.vault_manager.get_vault(self.user_did)

    def __exit__(self, exc_type, exc_val, exc_tb):
        dbsize_after = self.vault_manager.get_user_database_size(self.user_did, self.app_did)
        if dbsize_after != self.dbsize_before:
            self.vault_manager.update_user_databases_size(self.user_did, dbsize_after - self.dbsize_before)


class VaultManager:
    """ VaultManager is for other modules as a common class. """

    def __init__(self):
        self.mcli = MongodbClient()
        self.user_manager = UserManager()

    def get_vault_count(self) -> int:
        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        return col.count({})

    def get_vault(self, user_did) -> Vault:
        """ Get the vault for user or raise not-found exception.

        This method is also used to check the existence of the vault

        example:

            vault_manager.get_vault(user_did).check_storage_full().check_write_permission()

        """

        vault = self.__only_get_vault(user_did)

        # try to revert to free package plan
        return self.__try_to_downgrade_to_free(user_did, vault)

    def __only_get_vault(self, user_did):
        """ common method to all other method in this class """
        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)

        doc = col.find_one({VAULT_SERVICE_DID: user_did})
        if not doc:
            raise VaultNotFoundException()
        return Vault(**doc)

    def upgrade(self, user_did, plan: dict, vault: Vault = None):
        """ upgrade the vault to specific pricing plan """

        # Support vault = None to avoid recursive calling with 'get_vault()'
        if not vault:
            vault = self.__only_get_vault(user_did)

        # upgrading contains: vault size, expired date, plan
        start, end = PaymentConfig.get_plan_period(vault.get_plan(), vault.get_end_time(), plan)
        filter_ = {VAULT_SERVICE_DID: user_did}
        update = {
            VAULT_SERVICE_PRICING_USING: plan['name'],
            VAULT_SERVICE_MAX_STORAGE: int(plan["maxStorage"]) * 1024 * 1024,
            VAULT_SERVICE_START_TIME: start,
            VAULT_SERVICE_END_TIME: end,  # -1 means endless
            VAULT_SERVICE_MODIFY_TIME: start
        }

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, {'$set': update}, contains_extra=False)

    def __try_to_downgrade_to_free(self, user_did, vault: Vault):
        if PaymentConfig.is_free_plan(vault.get_plan_name()):
            return vault

        if not vault.is_expired():
            return vault

        # downgrade now
        self.upgrade(user_did, PaymentConfig.get_free_vault_plan(), vault=vault)
        return self.__only_get_vault(user_did)

    def recalculate_user_databases_size(self, user_did: str):
        """ Update all databases used size in vault """
        # Get all application DIDs of user DID, then get their sizes.
        app_dids = self.user_manager.get_apps(user_did)
        size = sum(list(map(lambda d: self.mcli.get_user_database_size(user_did, d), app_dids)))

        self.update_user_databases_size(user_did, size, is_reset=True)

    def get_user_database_size(self, user_did, app_did):
        return self.mcli.get_user_database_size(user_did, app_did)

    def update_user_databases_size(self, user_did, size: int, is_reset=False):
        self.__update_storage_size(user_did, size, False, is_reset=is_reset)

    def update_user_files_size(self, user_did, size: int, is_reset=False):
        self.__update_storage_size(user_did, size, True, is_reset=is_reset)

    def __update_storage_size(self, user_did, size, is_files: bool, is_reset=False):
        """ update files or databases usage of the vault

        :param user_did user DID
        :param size files&databases total size or increased size
        :param is_files files or databases storage usage
        :param is_reset: True means reset by size, else increase with size
        """

        if not is_reset and size == 0:
            return

        key = VAULT_SERVICE_FILE_USE_STORAGE if is_files else VAULT_SERVICE_DB_USE_STORAGE

        filter_ = {VAULT_SERVICE_DID: user_did}

        now = int(datetime.now().timestamp())
        if is_reset:
            update = {'$set': {key: size, VAULT_SERVICE_MODIFY_TIME: now}}
        else:
            update = {
                '$inc': {key: size},
                '$set': {VAULT_SERVICE_MODIFY_TIME: now}
            }

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, update, contains_extra=False)

    def update_vault_latest_access_time(self, user_did: str):
        filter_ = {VAULT_SERVICE_DID: user_did}
        update = {'$set': {VAULT_SERVICE_LATEST_ACCESS_TIME: int(datetime.now().timestamp())}}

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, update, contains_extra=False)

    def activate_vault(self, user_did, is_activate: bool):
        """ active or deactivate the vault without checking the existence of the vault """

        filter_ = {VAULT_SERVICE_DID: user_did}
        update = {'$set': {
            VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING if is_activate else VAULT_SERVICE_STATE_FREEZE,
            VAULT_SERVICE_MODIFY_TIME: int(datetime.now().timestamp())}}

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, update, contains_extra=False)

    def drop_vault_data(self, user_did):
        """ drop all data belong to user, include files and databases """

        # remove local user's vault folder
        path = hive_setting.get_user_vault_path(user_did)
        if path.exists():
            shutil.rmtree(path)

        # remove all databases belong to user's vault
        app_dids = self.user_manager.get_apps(user_did)
        for app_did in app_dids:
            self.mcli.drop_user_database(user_did, app_did)

    def count_app_files_total_size(self, user_did, app_did) -> int:
        """ only for batch 'count_vault_storage_job' """
        if not self.mcli.exists_user_database(user_did, app_did):
            return 0

        try:
            col = self.mcli.get_user_collection(user_did, app_did, COL_IPFS_FILES)
            files = col.find_many({"user_did": user_did, "app_did": app_did})
            # get total size of all user's application files
            return int(sum(map(lambda o: o["size"], files)))
        except CollectionNotFoundException as e:
            return 0
