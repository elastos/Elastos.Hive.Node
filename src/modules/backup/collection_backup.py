from datetime import datetime

from src import PaymentConfig
from src.utils.http_exception import BackupNotFoundException
from src.modules.database.mongodb_collection import mongodb_collection, CollectionName, MongodbCollection, \
    CollectionGenericField
from src.modules.backup.backup import Backup


class BackupRequestAction:
    BACKUP = 'backup'
    RESTORE = 'restore'


class BackupRequestState:
    STOP = 'stop'
    PROCESS = 'process'
    SUCCESS = 'success'
    FAILED = 'failed'
    STATE_MSG = 'state_msg'


@mongodb_collection(CollectionName.BACKUP_SERVER, is_management=True, is_internal=True)
class CollectionBackup(MongodbCollection):
    """ represents a backup service which keep the backup data of the vault. """

    # For backup service, include extra two fields: created, modified.
    USR_DID = CollectionGenericField.USR_DID
    PRICING_PLAN_NAME = "backup_using"
    STORAGE_MAX_SIZE = "max_storage"
    STORAGE_USED_SIZE = "use_storage"
    STARTED = "start_time"
    EXPIRED = "end_time"

    # For recording backup request from vault node.
    REQUEST_ACTION = 'req_action'
    REQUEST_STATE = 'req_state'
    REQUEST_STATE_MSG = 'req_state_msg'
    REQUEST_CID = 'req_cid'
    REQUEST_SHA256 = 'req_sha256'
    REQUEST_SIZE = 'req_size'
    REQUEST_PUBLIC_KEY = 'public_key'

    def get_all_backups(self) -> [Backup]:
        backups = self.find_many({})
        if not backups:
            raise BackupNotFoundException()

        return list(map(lambda doc: Backup(**doc), backups))

    def get_backup(self, user_did) -> Backup:
        """ Get the backup for user or raise not-found exception. """
        backup = self._only_get_backup(user_did)
        return self._try_to_downgrade_to_free(user_did, backup)

    def get_backup_count(self) -> int:
        return self.count({})

    def create_backup(self, user_did, price_plan):
        now = int(datetime.now().timestamp())
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60

        update = {"$setOnInsert": {
            self.PRICING_PLAN_NAME: price_plan['name'],
            self.STORAGE_MAX_SIZE: price_plan["maxStorage"] * 1024 * 1024,
            self.STORAGE_USED_SIZE: 0,
            self.STARTED: now,
            self.EXPIRED: int(end_time)
        }}

        self.update_one(self._get_filter(user_did), update, contains_extra=True, upsert=True)
        return self.get_backup(user_did)

    def update_backup(self, user_did, update):
        self.update_one(self._get_filter(user_did), {'$set': update}, contains_extra=True)

    def update_backup_storage_used_size(self, user_did, size):
        self.update_backup(user_did, {self.STORAGE_USED_SIZE, size})

    def update_backup_request(self, action, state, msg, cid, sha256, size, public_key):
        update = {
            BKSERVER_REQ_ACTION: BACKUP_REQUEST_ACTION_BACKUP,
            BKSERVER_REQ_STATE: BACKUP_REQUEST_STATE_PROCESS,
            BKSERVER_REQ_STATE_MSG: '50',  # start from 50%
            BKSERVER_REQ_CID: cid,
            BKSERVER_REQ_SHA256: sha256,
            BKSERVER_REQ_SIZE: size,
            BKSERVER_REQ_PUBLIC_KEY: public_key
        }
        col_backup.update_backup(g.usr_did, update)

    def upgrade_backup(self, user_did, plan: dict, backup=None):
        if not backup:
            backup = self.get_backup(user_did)

        # upgrading contains: backup size, expired date, plan
        start, end = PaymentConfig.get_plan_period(backup.get_plan(), backup.get_end_time(), plan)
        update = {
            self.PRICING_PLAN_NAME: plan['name'],
            self.STORAGE_MAX_SIZE: int(plan["maxStorage"]) * 1024 * 1024,
            self.STARTED: start,
            self.EXPIRED: end  # -1 means endless
        }

        self.update_one(self._get_filter(user_did), {'$set': update})

    def remove_backup(self, user_did):
        self.delete_one(self._get_filter(user_did))

    def _get_filter(self, user_did):
        return {self.USR_DID: user_did}

    def _only_get_backup(self, user_did):
        """ common method to all other method in this class """
        doc = self.find_one({self.USR_DID: user_did})
        if not doc:
            raise BackupNotFoundException()
        return Backup(**doc)

    def _try_to_downgrade_to_free(self, user_did, backup: Backup) -> Backup:
        if PaymentConfig.is_free_plan(backup.get_plan_name()):
            return backup

        if not backup.is_expired():
            return backup

        # downgrade now
        self.upgrade(user_did, PaymentConfig.get_free_backup_plan(), backup=backup)
        return self._only_get_backup(user_did)
