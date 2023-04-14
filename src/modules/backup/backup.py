from datetime import datetime

from src.utils.customize_dict import Dotdict
from src.utils.payment_config import PaymentConfig


class Backup(Dotdict):
    """ Represent a backup service which can be used to save backup data on the backup node side.

    TODO：move to file collection_backup.py
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_user_did(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.USR_DID]

    def get_plan(self):
        return PaymentConfig.get_backup_plan(self.get_plan_name())

    def get_plan_name(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.PRICING_PLAN_NAME]

    def is_expired(self):
        return 0 < self.get_end_time() < datetime.now().timestamp()

    def get_started_time(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.STARTED]

    def get_end_time(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.EXPIRED]

    def get_storage_quota(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.STORAGE_MAX_SIZE]

    def get_storage_used(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.STORAGE_USED_SIZE]

    def get_backup_request_action(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_ACTION]

    def get_backup_request_state(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_STATE]

    def get_backup_request_state_msg(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_STATE_MSG]

    def get_backup_request_cid(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_CID]

    def get_backup_request_sha256(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_SHA256]

    def get_backup_request_size(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_SIZE]

    def get_backup_request_public_key(self):
        from src.modules.backup.collection_backup import CollectionBackup
        return self[CollectionBackup.REQUEST_PUBLIC_KEY]
