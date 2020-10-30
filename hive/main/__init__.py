from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler
import logging

from hive.util.constants import HIVE_MODE_DEV, HIVE_MODE_TEST

logging.getLogger().level = logging.INFO


def init_app(app, mode):
    logging.getLogger("Hive").info("##############################")
    logging.getLogger("Hive").info("HIVE BACK-END IS STARTING")
    logging.getLogger("Hive").info("##############################")

    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)
    interceptor.init_app(app)
    if mode == HIVE_MODE_TEST:
        scheduler.scheduler_init(app, True)
    else:
        scheduler.scheduler_init(app, False)

