# -*- coding: utf-8 -*-

"""
The view of the pub/sub module.
"""
from flask_restful import Resource

from src.modules.pubsub.pubsub_service import PubSubService
from src.utils.http_request import RV


class RegisterMessage(Resource):
    def __init__(self):
        self.pubsub_service = PubSubService()

    def put(self, message_name):
        """ Register a new message.
        After this, the node client can use websocket to wait the pushing messages.

        .. :quickref: 10 Pub/Sub; Register

        **Request**:

        .. code-block:: json

            {
                "context": { # optional, default is caller self.
                    "targetDid": "<target did>",
                    "targetAppDid": "<target application did>"
                },
                "type": "countDocs",
                "body": {
                    "collections": [{name: ‘channel’, # count the newest inserted documents.
                        "field": "created" # the field needs to check. Here is new created on 1 hour.
                        "inside": 3600, # seconds
                    }],
                    "interval": 300, # trigger interval to check.
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
        self.pubsub_service.register_message(message_name)


class UnregisterMessage(Resource):
    def __init__(self):
        self.pubsub_service = PubSubService()

    def delete(self, message_name):
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
        self.pubsub_service.unregister_message(message_name)


class GetMessages(Resource):
    def __init__(self):
        self.pubsub_service = PubSubService()

    def get(self):
        """ Get all registered messages or specific message.

        .. :quickref: 10 Get; Get messages

        **Request**:

        .. code-block:: json

            {
                "name": "<message_name>" # optional
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            { # same as the registered content.
                "context": {
                    "targetDid": "<target did>",
                    "targetAppDid": "<target application did>"
                },
                "type": "countDocs",
                "body": {
                    "collections": [{name: ‘channel’,
                        "filter": {...}
                    }],
                    "interval": 300,
                }
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        name = RV.get_body().get_opt('name', str, None)

        return self.pubsub_service.get_messages(name)
