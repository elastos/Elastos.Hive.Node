import logging
from concurrent.futures import ThreadPoolExecutor

from flask_executor import Executor
from flask import g

from src.utils.consts import HIVE_MODE_TEST, COL_ORDERS, COL_ORDERS_PRICING_NAME, COL_RECEIPTS
from src.utils import hive_job
from src.utils.scheduler import count_vault_storage_really
from src.modules.scripting.collection_scripts_transaction import CollectionScriptsTransaction
from src.modules.database.mongodb_client import MongodbClient, mcli
from src.modules.backup.backup_client import bc
from src.modules.backup.backup_server import BackupServer

executor = Executor()
# DOCS https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
pool = ThreadPoolExecutor(1)


@executor.job
@hive_job('update_vault_databases_usage', 'executor')
def update_application_access_task(user_did: str, app_did: str, request, response):
    full_url = request.full_path
    request_len = request.content_length if request.content_length else 0
    response_len = response.content_length if response.content_length else 0
    total_len = request_len + response_len

    # record latest vault access time, include v1, v2 and database, files
    access_start_urls = [
        '/api/v1/db',
        '/api/v1/files',
        # '/api/v1/scripting', // not support, skip
        '/api/v2/vault/db',
        '/api/v2/vault/files',
        # '/api/v2/vault/scripting',
    ]

    need_update = any([full_url.startswith(url) for url in access_start_urls])
    if need_update:
        mcli.get_col_application().update_app_access(user_did, app_did, 1, total_len)
        return

    # handle v2 scripting module.
    scripting_stream_url = '/api/v2/vault/scripting/stream/'
    if full_url.startswith(scripting_stream_url):
        # download or upload by the transaction id of the script.
        transaction_id = full_url[len(scripting_stream_url):]
        if not transaction_id:
            return

        try:
            row_id, target_did, target_app_did, _ = CollectionScriptsTransaction.parse_transaction_id(transaction_id)
            mcli.get_col_application().update_app_access(target_did, target_app_did, 1, total_len)
        except:
            return

    scripting_url = '/api/v2/vault/scripting/'
    if full_url.startswith(scripting_url):
        # register or unregister a script
        is_register = request.method.upper() == 'GET' and '/' not in full_url[len(scripting_url):]
        is_unregister = request.method.upper() == 'DELETE'
        if is_register or is_unregister:
            mcli.get_col_application().update_app_access(user_did, app_did, 1, total_len)
            return

        # run script or run by url
        if not hasattr(g, 'script_context') or not g.script_context:
            return

        mcli.get_col_application().update_app_access(g.script_context.target_did, g.script_context.target_app_did, 1, total_len)


@executor.job
@hive_job('update_vault_databases_usage', 'executor')
def update_vault_databases_usage_task(user_did: str, full_url: str):
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
        mcli.get_col_vault().update_vault_latest_access(user_did)

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
        mcli.get_col_vault().recalculate_vault_database_used_size(user_did)
        logging.getLogger('AFTER REQUEST').info(f'Succeeded to update_vault_databases_usage({user_did}), {full_url}')


@hive_job('retry_backup_when_reboot', 'executor')
def retry_backup_when_reboot_task():
    """ retry maybe because interrupt by reboot

    1. handle all backup request in the vault node.
    2. handle all backup request in the backup node.
    """
    client, server = bc, BackupServer()
    client.retry_backup_request()
    server.retry_backup_request()


@hive_job('sync_app_dids', tag='executor')
def sync_app_dids_task():
    """ Used for syncing exist user_did's app_dids to the 'application' collection

    @deprecated Only used when hive node starting, it will be removed later.
    """

    vault_services = mcli.get_col_vault().get_all_vaults()

    for service in vault_services:
        user_did = service[mcli.get_col_vault().USER_DID]

        src_app_dids = mcli.get_col_register().get_register_app_dids(user_did)
        for app_did in src_app_dids:
            mcli.get_col_application().save_app(user_did, app_did)


@hive_job('count_vault_storage_executor', tag='executor')
def count_vault_storage_task():
    """ Recount the usage size of all vaults.

    @deprecated This will be removed later.
    """
    count_vault_storage_really()


@hive_job('rename_pricing_name_executor', tag='executor')
def rename_pricing_name():
    """ Rename pricing name: Free, Rookie, Advanced -> Basic, Standard, Premium

    - vault service
    - backup service
    - payment service: order and receipt

    @deprecated This will be removed later.
    """
    mcli = MongodbClient()

    def update_pricing_plan_name(collection_name, field):
        filter_, update_ = {field: "Free"}, {"$set": {field: "Basic"}}
        mcli.get_management_collection(collection_name).update_many(filter_, update_, contains_extra=False)
        filter_, update_ = {field: "Rookie"}, {"$set": {field: "Standard"}}
        mcli.get_management_collection(collection_name).update_many(filter_, update_, contains_extra=False)
        filter_, update_ = {field: "Advanced"}, {"$set": {field: "Premium"}}
        mcli.get_management_collection(collection_name).update_many(filter_, update_, contains_extra=False)

    def update_pricing_plan_name_ex(col, field_name):
        col.update_many_field_value(field_name, 'Free', 'Basic')
        col.update_many_field_value(field_name, 'Rookie', 'Standard')
        col.update_many_field_value(field_name, 'Advanced', 'Premium')

    update_pricing_plan_name_ex(mcli.get_col_vault(), mcli.get_col_vault().PRICING_USING)
    update_pricing_plan_name_ex(mcli.get_col_backup(), mcli.get_col_backup().PRICING_PLAN_NAME)
    update_pricing_plan_name(COL_ORDERS, COL_ORDERS_PRICING_NAME)
    update_pricing_plan_name(COL_RECEIPTS, COL_ORDERS_PRICING_NAME)


def init_executor(app, mode):
    """ executor for executing thread tasks """
    executor.init_app(app)

    if mode != HIVE_MODE_TEST:
        app.config['EXECUTOR_TYPE'] = 'thread'
        app.config['EXECUTOR_MAX_WORKERS'] = 5

        pool.submit(retry_backup_when_reboot_task)
        pool.submit(sync_app_dids_task)
        pool.submit(count_vault_storage_task)
        pool.submit(rename_pricing_name)
