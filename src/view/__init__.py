# -*- coding: utf-8 -*-
from hive.settings import hive_setting
from src.view import scripting


def init_app(app, mode):
    scripting.init_app(app, hive_setting)
