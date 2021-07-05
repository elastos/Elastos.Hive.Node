# -*- coding: utf-8 -*-
from hive.settings import hive_setting
from src.view import scripting, subscription, files, database, auth, backup, payment


def init_app(app, mode):
    auth.init_app(app, hive_setting)
    subscription.init_app(app, hive_setting)
    backup.init_app(app, hive_setting)
    scripting.init_app(app, hive_setting)
    files.init_app(app, hive_setting)
    database.init_app(app, hive_setting)
    payment.init_app(app, hive_setting)
