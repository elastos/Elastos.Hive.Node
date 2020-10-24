from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler
import logging


logging.getLogger().level = logging.INFO


def init_app(app, paused=False):
    logging.getLogger("Hive").info("##############################")
    logging.getLogger("Hive").info("HIVE BACK-END IS STARTING")
    logging.getLogger("Hive").info("##############################")

    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)
    interceptor.init_app(app)
    scheduler.scheduler_init(app, paused)
