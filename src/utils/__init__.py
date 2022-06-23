# -*- coding: utf-8 -*-
import logging
import traceback
import typing
from datetime import datetime

from sentry_sdk import capture_exception


def hive_job(name, tag='scheduler'):
    """ A decorator for any jobs, tasks which normally run on thread

    example:

        @hive_job('sync_app_dids')
        def sync_app_dids():  # normal function

        @scheduler.task(trigger='interval', id='daily_routine_job', days=1)
        @hive_job('count_vault_storage_job')
        def count_vault_storage_job():  # scheduler job
            ...

        @executor.job
        @hive_job('update_vault_databases_usage', tag='executor')
        def update_vault_databases_usage(user_did: str, full_url: str):  # executor task
            ...

    """

    def job_decorator(f: typing.Callable[..., None]) -> typing.Callable[..., None]:
        def wrapper(*args, **kwargs):
            logging.getLogger(tag).debug(f"{name} start: {str(datetime.now())}")

            try:
                f(*args, **kwargs)
            except Exception as e:
                msg = f'{name}: {str(e)}, {traceback.format_exc()}'
                logging.getLogger(tag).error(msg)
                capture_exception(error=Exception(f'{tag} UNEXPECTED: {msg}'))

            logging.getLogger(tag).debug(f"{name} end: {str(datetime.now())}")
        return wrapper
    return job_decorator
