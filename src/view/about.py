# -*- coding: utf-8 -*-

"""
About module to show some information of the node.
"""
from flask import Blueprint, request

from src.modules.about.about import About

blueprint = Blueprint('about', __name__)
about: About = About()


def init_app(app):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/about/version', methods=['GET'])
def get_version():
    """ Get the version of hive node. No authentication is required.

    .. :quickref: 08 About; Get the Version

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "major": 1,
            "minor": 0,
            "patch": 0
        }

    """
    return about.get_version()


@blueprint.route('/api/v2/about/commit_id', methods=['GET'])
def get_commit_id():
    """ Get the commit ID of hive node. No authentication is required.

    .. :quickref: 08 About; Get the Commit ID

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "commit_id": "<commit_id>"
        }

    """
    return about.get_commit_id()


@blueprint.route('/api/v2/echo', methods=['GET'])
def echo():
    """ only for test whether it can be connected with the hive node """
    content = request.args.get('content')
    return content if content else 'echo the parameter content'
