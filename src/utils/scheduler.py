# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import logging
import time
from flask_apscheduler import APScheduler

from src.utils.file_manager import fm
from src.utils_v1.common import get_temp_path

scheduler = APScheduler()


def scheduler_init(app):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()


@scheduler.task('interval', id='task_clean_temp_files', hours=6)
def task_clean_temp_files():
    """ Delete all temporary files created before 12 hours. """
    logging.info('[task_clean_temp_files] enter.')
    temp_path = get_temp_path()
    valid_timestamp = time.time() - 6 * 3600
    files = fm.get_files_recursively(temp_path)
    for f in files:
        if f.stat().st_mtime < valid_timestamp:
            f.unlink()
            logging.info(f'[task_clean_temp_files] Temporary file {f.as_posix()} removed.')
    logging.info('[task_clean_temp_files] leave.')


# Shutdown your cron thread if the web process is stopped
# atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == '__main__':
    task_clean_temp_files()
