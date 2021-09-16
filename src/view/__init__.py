# -*- coding: utf-8 -*-
from src.settings import hive_setting
from src.view import scripting, subscription, files, database, auth, backup, payment, ipfs, ipfs_backup, about


def init_app(app, mode):
    about.init_app(app, hive_setting)
    auth.init_app(app, hive_setting)
    subscription.init_app(app, hive_setting)
    backup.init_app(app, hive_setting)
    scripting.init_app(app, hive_setting)
    files.init_app(app, hive_setting)
    database.init_app(app, hive_setting)
    payment.init_app(app, hive_setting)
    ipfs.init_app(app, hive_setting)
    ipfs_backup.init_app(app, hive_setting)
