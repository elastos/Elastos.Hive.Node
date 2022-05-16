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
        return PaymentConfig.get_pricing_plan(self.doc[VAULT_SERVICE_PRICING_USING])

    def get_remain_days(self, dst_plan: dict):
        return PaymentConfig.get_current_plan_remain_days(self.get_plan(), self.doc[VAULT_SERVICE_END_TIME], dst_plan)


class VaultManager:
    """ VaultManager is for other modules as a common class. """

    def __init__(self):
        self.mcli = MongodbClient()

    def get_vault(self, user_did):
        """ Get the vault for user or raise not-found exception. """
        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)

        doc = col.find_one({VAULT_SERVICE_DID: user_did})
        if not doc:
            raise VaultNotFoundException()
        return Vault(doc)

    def upgrade(self, user_did, plan: dict):
        vault = self.get_vault(user_did)

        # upgrading contains: vault size, expired date, plan
        now, remain_days = datetime.utcnow().timestamp(), vault.get_remain_days(plan)
        end_time = -1 if plan['serviceDays'] == -1 else now + (plan['serviceDays'] + remain_days) * 24 * 60 * 60
        filter_ = {VAULT_SERVICE_DID: user_did}
        update = {VAULT_SERVICE_PRICING_USING: plan['name'],
                  VAULT_SERVICE_MAX_STORAGE: int(plan["maxStorage"]) * 1024 * 1024,
                  VAULT_SERVICE_START_TIME: now,
                  VAULT_SERVICE_END_TIME: end_time,
                  VAULT_SERVICE_MODIFY_TIME: now,
                  VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING}

        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)
        col.update_one(filter_, {'$set': update}, contains_extra=False)
