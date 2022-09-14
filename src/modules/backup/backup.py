from datetime import datetime

from src.modules.database.mongodb_client import MongodbClient, Dotdict
from src.utils.consts import COL_IPFS_BACKUP_SERVER, USR_DID, VAULT_BACKUP_SERVICE_USING, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, VAULT_BACKUP_SERVICE_USE_STORAGE
from src.utils.http_exception import BackupNotFoundException
from src.utils.payment_config import PaymentConfig


class Backup(Dotdict):
    """ Represent a backup service which can be used to save backup data on the backup node side. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_plan(self):
        return PaymentConfig.get_backup_plan(self.get_plan_name())

    def get_plan_name(self):
        return self[VAULT_BACKUP_SERVICE_USING]

    def is_expired(self):
        return 0 < self.get_end_time() < datetime.now().timestamp()

    def get_end_time(self):
        return self[VAULT_BACKUP_SERVICE_END_TIME]


class BackupManager:
    """ Run on the backup node side. """

    def __init__(self):
        self.mcli = MongodbClient()

    def get_all_backups(self):
        backups = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER).find_many({})
        if not backups:
            raise BackupNotFoundException()

        return list(map(lambda doc: Backup(**doc), backups))

    def get_backup_count(self) -> int:
        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)
        return col.count({})

    def get_backup(self, user_did) -> Backup:
        """ Get the backup for user or raise not-found exception. """
        backup = self.__only_get_backup(user_did)
        return self.__try_to_downgrade_to_free(user_did, backup)

    def __only_get_backup(self, user_did):
        """ common method to all other method in this class """
        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)

        doc = col.find_one({USR_DID: user_did})
        if not doc:
            raise BackupNotFoundException()
        return Backup(**doc)

    def create_backup(self, user_did, price_plan):
        now = int(datetime.now().timestamp())
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60

        filter_ = {USR_DID: user_did}
        update = {"$setOnInsert": {
            VAULT_BACKUP_SERVICE_USING: price_plan['name'],
            VAULT_BACKUP_SERVICE_MAX_STORAGE: price_plan["maxStorage"] * 1024 * 1024,
            VAULT_BACKUP_SERVICE_USE_STORAGE: 0,
            VAULT_BACKUP_SERVICE_START_TIME: now,
            VAULT_BACKUP_SERVICE_END_TIME: int(end_time)
        }}

        self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER).update_one(filter_, update, contains_extra=True, upsert=True)
        return self.get_backup(user_did)

    def update_backup(self, user_did, update):
        filter_ = {USR_DID: user_did}
        self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER).update_one(filter_, {'$set': update}, contains_extra=True)

    def upgrade(self, user_did, plan: dict, backup=None):
        if not backup:
            backup = self.get_backup(user_did)

        # upgrading contains: backup size, expired date, plan
        start, end = PaymentConfig.get_plan_period(backup.get_plan(), backup.get_end_time(), plan)
        filter_ = {USR_DID: user_did}
        update = {
            VAULT_BACKUP_SERVICE_USING: plan['name'],
            VAULT_BACKUP_SERVICE_MAX_STORAGE: int(plan["maxStorage"]) * 1024 * 1024,
            VAULT_BACKUP_SERVICE_START_TIME: start,
            VAULT_BACKUP_SERVICE_END_TIME: end  # -1 means endless
        }

        col = self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER)
        col.update_one(filter_, {'$set': update})

    def __try_to_downgrade_to_free(self, user_did, backup: Backup) -> Backup:
        if PaymentConfig.is_free_plan(backup.get_plan_name()):
            return backup

        if not backup.is_expired():
            return backup

        # downgrade now
        self.upgrade(user_did, PaymentConfig.get_free_backup_plan(), backup=backup)
        return self.__only_get_backup(user_did)

    def remove_backup(self, user_did):
        filter_ = {USR_DID: user_did}

        self.mcli.get_management_collection(COL_IPFS_BACKUP_SERVER).delete_one(filter_)
