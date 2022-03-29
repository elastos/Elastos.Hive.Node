import threading

from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler, view_internal, \
    view_backup, view_pubsub
import logging

from hive.util.constants import HIVE_MODE_TEST
from ..settings import hive_setting

from ..util.did.did_init import init_did_backend
from ..util.payment.vault_service_manage import count_vault_storage_job

logging.getLogger().level = logging.INFO


class RefreshVaultStorageUsageThread(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        # Reset the storage size of all vaults when initialize.
        try:
            logging.info(f'[RefreshVaultStorageUsageThread] Start init all vaults usage.')
            count_vault_storage_job()
            logging.info(f'[RefreshVaultStorageUsageThread] Init vault usage successfully')
        except Exception as e:
            logging.error(f'[RefreshVaultStorageUsageThread] Init vault usage failed {str(e)}')


def init_app(app, mode):
    hive_setting.init_config()
    logging.getLogger('v1_init').info('enter init_app')

    init_did_backend()
    interceptor.init_app(app)
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)
    view_internal.init_app(app, mode)
    view_backup.init_app(app, mode)
    view_pubsub.init_app(app, mode)
    if mode == HIVE_MODE_TEST:
        scheduler.scheduler_init(app, paused=True)
    else:
        scheduler.scheduler_init(app, paused=False)

    RefreshVaultStorageUsageThread().start()
    logging.getLogger('v1_init').info('leave init_app')
