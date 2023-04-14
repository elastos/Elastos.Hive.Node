# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import logging
import time
from pathlib import Path

from flask_apscheduler import APScheduler

from src.utils import hive_job
from src.modules.files.local_file import LocalFile
from src.modules.database.mongodb_client import mcli

scheduler = APScheduler()


def scheduler_init(app):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()


def count_vault_storage_really():
    vault_services, col_application = mcli.get_col_vault().get_all_vaults(), mcli.get_col_application()

    for service in vault_services:
        user_did = service[mcli.get_col_vault().USER_DID]

        # get files and databases total size
        app_dids = col_application.get_app_dids(user_did)
        files_used_size = sum(map(lambda app_did: col_application.get_app_total_files_size(user_did, app_did), app_dids))
        database_used_size = sum(map(lambda app_did: col_application.get_app_total_database_size(user_did, app_did), app_dids))

        mcli.get_col_vault().update_vault_file_used_size(user_did, files_used_size)
        mcli.get_col_vault().update_vault_database_used_size(user_did, database_used_size)


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
