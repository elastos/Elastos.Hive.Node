# -*- coding: utf-8 -*-

"""
About module to show some information of the node.
"""
from flask import Blueprint

from src.modules.about.about import About

blueprint = Blueprint('about', __name__)
about: About = None


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global about
    about = About(app, hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/about/version', methods=['GET'])
def get_version():
    return about.get_version()


@blueprint.route('/api/v2/about/commit_id', methods=['GET'])
def get_commit_id():
    return about.get_commit_id()
