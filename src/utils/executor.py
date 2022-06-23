import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

from flask_executor import Executor
from sentry_sdk import capture_exception

from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.ipfs.ipfs_backup_client import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.vault import VaultManager
from src.utils import hive_job
from src.utils.db_client import cli
from src.utils.scheduler import count_vault_storage_really
from src.utils_v1.constants import VAULT_SERVICE_COL, VAULT_SERVICE_DID

executor = Executor()
# DOCS https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
pool = ThreadPoolExecutor(1)


@executor.job
@hive_job('update_vault_databases_usage', 'executor')
def update_vault_databases_usage_task(user_did: str, full_url: str):
    from src.modules.subscription.vault import VaultManager

    try:
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
            VaultManager().recalculate_user_databases_size(user_did)
            logging.getLogger('AFTER REQUEST').info(f'Succeeded to update_vault_databases_usage({user_did}), {full_url}')
    except Exception as e:
        msg = f'update_vault_databases_usage: {str(e)}, {traceback.format_exc()}'
        logging.getLogger('AFTER REQUEST').error(msg)
        capture_exception(error=Exception(f'AFTER REQUEST UNEXPECTED: {msg}'))


@hive_job('retry_backup_when_reboot', 'executor')
def retry_backup_when_reboot_task():
    """ retry maybe because interrupt by reboot

    1. handle all backup request in the vault node.
    2. handle all backup request in the backup node.

    """

    client, server = IpfsBackupClient(), IpfsBackupServer()
    # TODO: get backup requests separately from COL_IPFS_BACKUP_CLIENT and COL_IPFS_BACKUP_SERVER
    user_dids = cli.get_all_user_dids()
    logging.info(f'[retry_ipfs_backup] get {len(user_dids)} users')
    for user_did in user_dids:
        client.retry_backup_request(user_did)
        server.retry_backup_request(user_did)


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


def init_executor(app):
    """ executor for executing thread tasks """
    executor.init_app(app)
    app.config['EXECUTOR_TYPE'] = 'thread'
    app.config['EXECUTOR_MAX_WORKERS'] = 5

    pool.submit(retry_backup_when_reboot_task)
    pool.submit(sync_app_dids_task)
    pool.submit(count_vault_storage_task)
