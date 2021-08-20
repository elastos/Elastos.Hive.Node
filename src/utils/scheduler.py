# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import logging

import pymongo
from flask_apscheduler import APScheduler

from src.utils.consts import COL_IPFS_FILES, COL_IPFS_FILES_IPFS_CID, COL_IPFS_FILES_PATH, DID, APP_DID
from src.utils.db_client import cli
from src.utils.file_manager import fm

scheduler = APScheduler()


def scheduler_init(app):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()


@scheduler.task(trigger='interval', id='task_upload_ipfs_files', minutes=5)
def task_upload_ipfs_files():
    logging.info('[task_upload_ipfs_files] enter.')
    names = cli.get_all_database_names()
    for db_name in names:
        if db_name.startswith('hive_user_db'):
            upload_ipfs_files_by_db(db_name)


def upload_ipfs_files_by_db(db_name):
    # find 10 docs and ordered by ascending.
    col_filter = {COL_IPFS_FILES_IPFS_CID: {'$exists': True, '$eq': None}}
    options = {'limit': 10, 'sort': [('modified', pymongo.ASCENDING), ]}
    file_docs = cli.find_many_origin(db_name, COL_IPFS_FILES, col_filter, is_raise=False, options=options)
    logging.info(f'[task_upload_ipfs_files] get {len(file_docs) if file_docs else 0} '
                 f'{db_name} files for uploading to ipfs node')
    if not file_docs:
        return

    for doc in file_docs:
        try:
            cid = fm.ipfs_uploading_file(doc[DID], doc[COL_IPFS_FILES_PATH])
            col_filter = {DID: doc[DID], APP_DID: doc[APP_DID], COL_IPFS_FILES_PATH: doc[COL_IPFS_FILES_PATH]}
            cli.update_one_origin(db_name, COL_IPFS_FILES,
                                  col_filter, {'$set': {COL_IPFS_FILES_IPFS_CID: cid}}, is_extra=True)
        except Exception as e:
            logging.error(f'[task_upload_ipfs_files] failed upload file to ipfs with exception: {str(e)}')


# Shutdown your cron thread if the web process is stopped
# atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == '__main__':
    task_upload_ipfs_files()
