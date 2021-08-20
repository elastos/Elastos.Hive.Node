import sentry_sdk

from . import view, view_db, view_file, view_scripting, view_payment, interceptor, scheduler, view_internal, \
    view_backup, view_pubsub
import logging

from hive.util.constants import HIVE_MODE_DEV, HIVE_MODE_TEST
from ..settings import hive_setting
from sentry_sdk.integrations.flask import FlaskIntegration

from ..util.did.did_init import init_did_backend
from ..util.payment.vault_service_manage import count_vault_storage_job

logging.getLogger().level = logging.INFO


def init_app(app, mode):
    logging.getLogger("Hive").info("##############################")
    logging.getLogger("Hive").info("HIVE BACK-END IS STARTING")
    logging.getLogger("Hive").info("##############################")

    if mode != HIVE_MODE_TEST and hive_setting.HIVE_SENTRY_DSN != "":
        sentry_sdk.init(
            dsn=hive_setting.HIVE_SENTRY_DSN,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0
        )

    init_did_backend()
    interceptor.init_app(app)
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    view_payment.init_app(app)
    view_internal.init_app(app, mode)
    view_backup.init_app(app, mode)
    view_pubsub.init_app(app, mode)
    if mode == HIVE_MODE_TEST:
        scheduler.scheduler_init(app, paused=True)
    else:
        scheduler.scheduler_init(app, paused=False)
    # Reset the storage size of all vaults when initialize.
    try:
        count_vault_storage_job()
        logging.getLogger("Hive").info(f'Init vault usage successfully')
    except Exception as e:
        logging.getLogger("Hive").error(f'Init vault usage failed {str(e)}')
