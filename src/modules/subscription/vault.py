from datetime import datetime

from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient, Dotdict
from src.utils.db_client import VAULT_SERVICE_STATE_RUNNING
from src.utils.http_exception import InsufficientStorageException, VaultNotFoundException
from src.utils_v1.constants import VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_COL, \
    VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE
from src.utils_v1.payment.payment_config import PaymentConfig


class Vault(Dotdict):
    """ Represents a user vault """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_database_usage(self):
        return self.db_use_storage

    def get_storage_gap(self):
        return int(self.max_storage - (self.file_use_storage + self.db_use_storage))

    def is_storage_full(self):
        return self.get_storage_gap() <= 0

    def check_storage(self):
        if self.is_storage_full():
            raise InsufficientStorageException()

    def get_plan(self):
        return PaymentConfig.get_pricing_plan(self.pricing_using)

    def get_plan_name(self):
        return self.pricing_using

    def is_expired(self):
        return 0 < self.end_time < datetime.utcnow().timestamp()

    def get_end_time(self):
        return self.end_time


class AppSpaceDetector:
    """ can only detect the database space size changes

    Files storage size changing can be checked by file size accurately.
    """

    def __init__(self, user_did, app_did):
        self.user_did, self.app_did = user_did, app_did
        self.vault_manager = VaultManager()
        self.dbsize_before = self.vault_manager.get_user_database_size(user_did, app_did)

    def __enter__(self):
        return self.vault_manager.get_vault(self.user_did)

    def __exit__(self, exc_type, exc_val, exc_tb):
        dbsize_after = self.vault_manager.get_user_database_size(self.user_did, self.app_did)
        self.vault_manager.update_user_database_size(self.user_did, dbsize_after - self.dbsize_before)


class VaultManager:
    """ VaultManager is for other modules as a common class. """

    def __init__(self):
        self.mcli = MongodbClient()
        self.user_manager = UserManager()

    def get_vault(self, user_did) -> Vault:
        """ Get the vault for user or raise not-found exception.

        This method is also used to check the existence of the vault
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
            VAULT_SERVICE_MODIFY_TIME: start,
            VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING
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

    def update_database_size(self, user_did: str):
        """ Get all databases of user DID and sum the sizes. """
        # Get all application DIDs of user DID, then get their sizes.
        app_dids = self.user_manager.get_all_app_dids(user_did)
        size = sum(list(map(lambda d: self.mcli.get_user_database_size(user_did, d), app_dids)))

        self.update_user_database_size(user_did, size)

    def get_user_database_size(self, user_did, app_did):
        return self.mcli.get_user_database_size(user_did, app_did)

    def update_user_database_size(self, user_did, size: int, delta_size: bool = False):
        new_size = self.get_vault(user_did).get_database_usage() + size if delta_size else size

        filter_ = {VAULT_SERVICE_DID: user_did}
        update = {
            VAULT_SERVICE_DB_USE_STORAGE: int(new_size),
            VAULT_SERVICE_MODIFY_TIME: int(datetime.utcnow().timestamp())
        }

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, {'$set': update}, contains_extra=False)
