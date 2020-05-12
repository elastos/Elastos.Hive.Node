#!/usr/bin/env python
# coding=utf-8


from eve import Eve
from flask import request, jsonify

from hive.main.hive_mongo import HiveMongo
from hive.util.auth import HiveTokenAuth
from hive import main

DEFAULT_APP_NAME = 'hive_node'

configs = {
    'development': "settings_dev.py",
    'testing': "settings_test.py",
    'production': "settings.py",
    'default': "settings_dev.py"
}


def create_app(config='default'):
    app = Eve(auth=HiveTokenAuth, settings=configs[config])
    main.init_app(app)
    return app

