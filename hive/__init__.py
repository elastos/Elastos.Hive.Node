from flask import Flask

from hive import main

DEFAULT_APP_NAME = 'Hive Node'


def create_app():
    app = Flask(DEFAULT_APP_NAME)
    main.init_app(app)
    return app
