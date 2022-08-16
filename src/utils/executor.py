import logging
from concurrent.futures import ThreadPoolExecutor

from flask_executor import Executor

from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.backup.backup_client import BackupClient
from src.modules.backup.backup_server import BackupServer
from src.modules.subscription.vault import VaultManager
from src.utils import hive_job
from src.utils.scheduler import count_vault_storage_really
from src.utils.consts import VAULT_SERVICE_COL, VAULT_SERVICE_DID, HIVE_MODE_TEST

executor = Executor()
# DOCS https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
pool = ThreadPoolExecutor(1)


@executor.job
@hive_job('update_vault_databases_usage', 'executor')
def update_vault_databases_usage_task(user_did: str, full_url: str):
    from src.modules.subscription.vault import VaultManager
    vault_manager = VaultManager()

    # record latest vault access time, include v1, v2 and database, files, scripting (caller)
    access_start_urls = [
        '/api/v1/db',
        '/api/v1/files',
        '/api/v1/scripting',
        '/api/v2/vault/db',
        '/api/v2/vault/files',
        '/api/v2/vault/scripting',
    ]

    need_update = any([full_url.startswith(url) for url in access_start_urls])
    if need_update:
        vault_manager.update_vault_latest_access_time(user_did)

    # v1, just consider auth, subscription, database, files, subscripting
    exclude_start_urls = [
        '/api/v1/echo',
        '/api/v1/hive',  # about
        '/api/v1/did',
        '/api/v1/service/vault',  # subscription
        '/api/v2/node',
        '/api/v2/about',
        '/api/v2/did',
        '/api/v2/subscription',
        '/api/v2/payment',
        '/api/v2/provider',
    ]
    need_update = all([not full_url.startswith(url) for url in exclude_start_urls])
    if need_update:
        vault_manager.recalculate_user_databases_size(user_did)
        logging.getLogger('AFTER REQUEST').info(f'Succeeded to update_vault_databases_usage({user_did}), {full_url}')


@hive_job('retry_backup_when_reboot', 'executor')
def retry_backup_when_reboot_task():
    """ retry maybe because interrupt by reboot

    1. handle all backup request in the vault node.
    2. handle all backup request in the backup node.
    """
    client, server = BackupClient(), BackupServer()
    client.retry_backup_request()
    server.retry_backup_request()


@hive_job('sync_app_dids', tag='executor')
def sync_app_dids_task():
    """ Used for syncing exist user_did's app_dids to the 'application' collection

    @deprecated Only used when hive node starting, it will be removed later.
    """

    mcli, user_manager, vault_manager = MongodbClient(), UserManager(), VaultManager()

    col = mcli.get_management_collection(VAULT_SERVICE_COL)
    vault_services = col.find_many({VAULT_SERVICE_DID: {'$exists': True}})  # cursor

    for service in vault_services:
        user_did = service[VAULT_SERVICE_DID]

        src_app_dids = user_manager.get_temp_app_dids(user_did)
        for app_did in src_app_dids:
            user_manager.add_app_if_not_exists(user_did, app_did)


@hive_job('count_vault_storage_executor', tag='executor')
def count_vault_storage_task():
    count_vault_storage_really()


def init_executor(app, mode):
    """ executor for executing thread tasks """
    executor.init_app(app)

    if mode != HIVE_MODE_TEST:
        app.config['EXECUTOR_TYPE'] = 'thread'
        app.config['EXECUTOR_MAX_WORKERS'] = 5

        pool.submit(retry_backup_when_reboot_task)
        pool.submit(sync_app_dids_task)
        pool.submit(count_vault_storage_task)
