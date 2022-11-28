# -*- coding: utf-8 -*-

"""
The view of the pub/sub module.
"""
from flask_restful import Resource


class RegisterMessage(Resource):
    def __init__(self):
        ...

    def put(self, message_name):
        """ Register a new message.
        After this, the node client can use websocket to wait the pushing messages.

        .. :quickref: 10 Pub/Sub; Register

        **Request**:

        .. code-block:: json

            {
                "context": {
                    "targetDid": "<target did>",
                    "targetAppDid": "<target application did>"
                },
                "type": "countDocs",
                "body": {
                    "collections": [{name: ‘channel’, # count the newest inserted documents.
                        "filter": {...} # filter to count the documents.
                    }],
                    "interval": 300, # trigger interval.
                }
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "acknowledged": true,
                "matched_count": 0,
                "modified_count": 1,
                "upserted_id": "<object id>"
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        """
        ...


class UnregisterMessage(Resource):
    def __init__(self):
        ...

    def delete(self, script_name):
        """ Unregister the message.

        .. :quickref: 10 Pub/Sub; Unregister

        **Request**:

        .. code-block:: json

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 204 No Content

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        ...
