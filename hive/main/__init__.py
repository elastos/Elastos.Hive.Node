from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler, view_backup
import logging

from hive.util.constants import HIVE_MODE_DEV, HIVE_MODE_TEST

logging.getLogger().level = logging.INFO


def init_app(app, mode):
    logging.getLogger("Hive").info("##############################")
    logging.getLogger("Hive").info("HIVE BACK-END IS STARTING")
    logging.getLogger("Hive").info("##############################")

    interceptor.init_app(app)
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)
    view_backup.init_app(app, mode)
    if mode == HIVE_MODE_TEST:
        scheduler.scheduler_init(app, paused=True)
    else:
        scheduler.scheduler_init(app, paused=False)
