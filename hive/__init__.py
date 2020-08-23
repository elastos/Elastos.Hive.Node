import os
from eve import Eve

from hive.main.hive_mongo import HiveMongo
from hive.util.auth import HiveTokenAuth
from hive import main

DEFAULT_APP_NAME = 'Hive Node'

configs = {
    'development': "hive/settings_dev.py",
    'testing': "hive/settings_test.py",
    'production': "hive/settings.py",
    'default': "hive/settings_dev.py"
}


def create_app(config='default'):
    app = Eve(auth=HiveTokenAuth, settings=os.path.abspath(configs[config]))
    main.init_app(app)
    return app
