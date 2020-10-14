from . import view, view_db, view_file, view_scripting, interceptor
import logging


logger = logging.getLogger()
logger.level = logging.INFO


def init_app(app):
    logging.getLogger("Hive").info("##############################")
    logging.getLogger("Hive").info("HIVE BACK-END IS STARTING")
    logging.getLogger("Hive").info("##############################")

    # print("##############################")
    # print("HIVE BACK-END IS STARTING")
    # print("##############################")
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    interceptor.init_app(app)
