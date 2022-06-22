import logging
from datetime import datetime

from flask_apscheduler import APScheduler

from hive.util.payment.vault_order import check_pay_order_timeout_job, check_wait_order_tx_job
from hive.util.payment.vault_service_manage import proc_expire_vault_job

scheduler = APScheduler()


def scheduler_init(app, paused=False):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start(paused)


def scheduler_stop():
    if scheduler.running:
        scheduler.shutdown()


def scheduler_resume():
    scheduler.resume()


def scheduler_pause():
    scheduler.pause()


@scheduler.task(trigger='interval', id='expire_vault_job', days=1)
def expire_vault_job():
    logging.getLogger("Hive scheduler").debug(f"expire_vault_job start: {str(datetime.utcnow())}")
    proc_expire_vault_job()
    logging.getLogger("Hive scheduler").debug(f"expire_vault_job end: {str(datetime.utcnow())}")


@scheduler.task(trigger='interval', id='check_order_timeout_job', minutes=1)
def check_order_timeout_job():
    # logging.getLogger("Hive scheduler").debug(f"check_order_timeout_job start: {str(datetime.utcnow())}")
    check_pay_order_timeout_job()
    # logging.getLogger("Hive scheduler").debug(f"check_order_timeout_job end: {str(datetime.utcnow())}")


@scheduler.task(trigger='interval', id='wait_orders_tx_job', minutes=1)
def wait_orders_tx_job():
    # logging.getLogger("Hive scheduler").debug(f"wait_orders_tx_job start: {str(datetime.utcnow())}")
    check_wait_order_tx_job()
    # logging.getLogger("Hive scheduler").debug(f"wait_orders_tx_job end: {str(datetime.utcnow())}")
