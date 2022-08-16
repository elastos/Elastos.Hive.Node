# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import logging
import time
from datetime import datetime
from pathlib import Path

from flask_apscheduler import APScheduler

from src.utils.consts import VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_MODIFY_TIME
from src.utils import hive_job
from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.files.local_file import LocalFile
from src.modules.subscription.vault import VaultManager

scheduler = APScheduler()


def scheduler_init(app):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()


def count_vault_storage_really():
    mcli, user_manager, vault_manager = MongodbClient(), UserManager(), VaultManager()
    now = int(datetime.now().timestamp())

    col = mcli.get_management_collection(VAULT_SERVICE_COL)
    vault_services = col.find_many({VAULT_SERVICE_DID: {'$exists': True}})  # cursor

    for service in vault_services:
        user_did = service[VAULT_SERVICE_DID]

        # get files and databases total size
        app_dids = user_manager.get_apps(user_did)
        files_size = sum(map(lambda app_did: vault_manager.count_app_files_total_size(user_did, app_did), app_dids))
        dbs_size = sum(map(lambda app_did: mcli.get_user_database_size(user_did, app_did), app_dids))

        # update sizes into the vault information
        filter_ = {"_id": service["_id"]}
        update = {"$set": {
            VAULT_SERVICE_FILE_USE_STORAGE: files_size,
            VAULT_SERVICE_DB_USE_STORAGE: dbs_size,
            VAULT_SERVICE_MODIFY_TIME: now}}
        col.update_one(filter_, update, contains_extra=False)


@scheduler.task(trigger='interval', id='daily_routine_job', days=1)
@hive_job('count_vault_storage_job')
def count_vault_storage_job():
    count_vault_storage_really()


@scheduler.task('interval', id='task_clean_temp_files', hours=6)
@hive_job('clean_temp_files_job')
def clean_temp_files_job():
    """ Delete all temporary files created before 12 hours. """

    temp_path = Path(hive_setting.get_temp_dir())
    valid_timestamp = time.time() - 6 * 3600
    files = LocalFile.get_files_recursively(temp_path)
    for f in files:
        if f.stat().st_mtime < valid_timestamp:
            f.unlink()
            logging.getLogger("scheduler").debug(f'clean_temp_files_job() Temporary file {f.as_posix()} removed.')


# Shutdown your cron thread if the web process is stopped
# atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == '__main__':
    # init logger
    from src import create_app, hive_setting

    create_app()

    # sync_app_dids()
    # count_vault_storage_job()
    # clean_temp_files_job()
