# -*- coding: utf-8 -*-
from hive.settings import hive_setting
from src.view import scripting
from src.view import subscription
from src.view import files


def init_app(app, mode):
    scripting.init_app(app, hive_setting)
    subscription.init_app(app, hive_setting)
    files.init_app(app, hive_setting)