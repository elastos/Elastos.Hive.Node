# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import atexit
import logging

import pymongo
from flask_apscheduler import APScheduler

from hive.util.constants import DID_INFO_DB_NAME
from src.utils.consts import COL_IPFS_FILES, COL_IPFS_FILES_IPFS_CID, COL_IPFS_FILES_PATH, DID, APP_DID
from src.utils.db_client import cli
from src.utils.file_manager import fm

scheduler = APScheduler()


def scheduler_init(app):
    scheduler.init_app(app)
    scheduler.start()


@scheduler.task(trigger='interval', id='task_upload_ipfs_files', minutes=10)
def task_upload_ipfs_files():
    logging.info('[task_upload_ipfs_files] enter.')
    # find 10 docs and ordered by ascending.
    col_filter = {COL_IPFS_FILES_IPFS_CID: None}
    options = {'limit': 10, 'sort': [('modified', pymongo.ASCENDING), ]}
    file_docs = cli.find_many_origin(DID_INFO_DB_NAME, COL_IPFS_FILES, col_filter, is_raise=False, options=options)
    if not file_docs:
        logging.info('[task_upload_ipfs_files] no files need be uploading to ipfs node.')
        return
    for doc in file_docs:
        cid = fm.ipfs_uploading_file(doc[COL_IPFS_FILES_PATH])
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_FILES, {DID: doc[DID],
                                                                 APP_DID: doc[APP_DID],
                                                                 COL_IPFS_FILES_PATH: doc[COL_IPFS_FILES_PATH]},
                              {'$set': {COL_IPFS_FILES_IPFS_CID: cid}}, is_extra=True)


# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: scheduler.shutdown(wait=False))
