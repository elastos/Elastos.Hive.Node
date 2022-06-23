import logging

from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler, view_internal, \
    view_backup, view_pubsub
from hive.util.constants import HIVE_MODE_TEST

logging.getLogger().level = logging.INFO


def init_app(app, mode):
    logging.getLogger('v1_init').info('enter init_app')

    interceptor.init_app(app)
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)  # including vault create/remove

    # @deprecated unused modules, but keep here
    view_internal.init_app(app, mode)
    view_backup.init_app(app, mode)
    view_pubsub.init_app(app, mode)

    if mode == HIVE_MODE_TEST:
        scheduler.scheduler_init(app, paused=True)
    else:
        scheduler.scheduler_init(app, paused=False)

    logging.getLogger('v1_init').info('leave init_app')
