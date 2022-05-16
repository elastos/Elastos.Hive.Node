from datetime import datetime

from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_IPFS_BACKUP_SERVER, USR_DID
from src.utils.http_exception import BackupNotFoundException
from src.utils_v1.constants import VAULT_SERVICE_PRICING_USING, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME
from src.utils_v1.payment.payment_config import PaymentConfig


class Backup:
    """ Represent a backup service which can be used to save backup data. """

    def __init__(self, doc):
        self.doc = doc

    def get_plan(self):
        return PaymentConfig.get_backup_plan(self.doc[VAULT_SERVICE_PRICING_USING])

    def get_remain_days(self, dst_plan: dict):
        return PaymentConfig.get_current_plan_remain_days(self.get_plan(), self.doc[VAULT_BACKUP_SERVICE_END_TIME], dst_plan)


class BackupManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def get_backup(self, user_did):
        """ Get the backup for user or raise not-found exception. """
        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)

        doc = col.find_one({USR_DID: user_did})
        if not doc:
            raise BackupNotFoundException()
        return Backup(doc)

    def upgrade(self, user_did, plan: dict):
        backup = self.get_backup(user_did)

        # upgrading contains: backup size, expired date, plan
        now, remain_days = datetime.utcnow().timestamp(), backup.get_remain_days(plan)
        end_time = -1 if plan['serviceDays'] == -1 else now + (plan['serviceDays'] + remain_days) * 24 * 60 * 60
        filter_ = {USR_DID: user_did}
        update = {VAULT_BACKUP_SERVICE_USING: plan['name'],
                  VAULT_BACKUP_SERVICE_MAX_STORAGE: int(plan["maxStorage"]) * 1024 * 1024,
                  VAULT_BACKUP_SERVICE_START_TIME: now,
                  VAULT_BACKUP_SERVICE_END_TIME: end_time}

        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)
        col.update_one(filter_, {'$set': update})
