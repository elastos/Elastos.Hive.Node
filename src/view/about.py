# -*- coding: utf-8 -*-

"""
About module to show some information of the node.
"""
from flask_restful import Resource

from src.modules.about.about import About


class Version(Resource):
    def __init__(self):
        self.about = About()

    def get(self):
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
        return self.about.get_version()


class CommitId(Resource):
    def __init__(self):
        self.about = About()

    def get(self):
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
        return self.about.get_commit_id()


class NodeInfo(Resource):
    def __init__(self):
        self.about = About()

    def get(self):
        """ Get the information of this hive node.

        .. :quickref: 08 About; Get Node Information

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "service_did": <str>,
                "owner_did": <str>,
                "ownership_presentation": <str>,
                "name": <str>,
                "email": <str>,
                "description": <str>,
                "version": <str>,
                "last_commit_id": <str>
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        """

        return self.about.get_node_info()
