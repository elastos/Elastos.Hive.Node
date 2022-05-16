from datetime import datetime

from src.modules.database.mongodb_client import MongodbClient
from src.utils.db_client import VAULT_SERVICE_STATE_RUNNING
from src.utils.http_exception import InsufficientStorageException, VaultNotFoundException
from src.utils_v1.constants import VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_COL, \
    VAULT_SERVICE_DID, VAULT_SERVICE_PRICING_USING, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE
from src.utils_v1.payment.payment_config import PaymentConfig


class Vault:
    """ Represents a user vault """

    def __init__(self, doc):
        self.doc = doc

    def get_storage_gap(self):
        return int(self.doc[VAULT_SERVICE_MAX_STORAGE] - (self.doc[VAULT_SERVICE_FILE_USE_STORAGE] + self.doc[VAULT_SERVICE_DB_USE_STORAGE]))

    def is_storage_full(self):
        return self.get_storage_gap() <= 0

    def check_storage(self):
        if self.is_storage_full():
            raise InsufficientStorageException()

    def get_plan(self):
        return PaymentConfig.get_pricing_plan(self.get_plan_name())

    def get_plan_name(self):
        return self.doc[VAULT_SERVICE_PRICING_USING]

    def is_expired(self):
        return 0 < self.doc[VAULT_SERVICE_END_TIME] < datetime.utcnow().timestamp()

    def get_end_time(self):
        return self.doc[VAULT_SERVICE_END_TIME]


class VaultManager:
    """ VaultManager is for other modules as a common class. """

    def __init__(self):
        self.mcli = MongodbClient()

    def get_vault(self, user_did) -> Vault:
        """ Get the vault for user or raise not-found exception. """
        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)

        doc = col.find_one({VAULT_SERVICE_DID: user_did})
        if not doc:
            raise VaultNotFoundException()

        # try to revert to free package plan
        return self.try_to_downgrade_to_free(user_did, Vault(doc))

    def upgrade(self, user_did, plan: dict):
        vault = self.get_vault(user_did)

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

    def try_to_downgrade_to_free(self, user_did, vault: Vault):
        if PaymentConfig.is_free_plan(vault.get_plan_name()):
            return vault

        if not vault.is_expired():
            return vault

        # downgrade now
        self.upgrade(user_did, PaymentConfig.get_free_vault_plan())
        return vault
