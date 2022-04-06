# -*- coding: utf-8 -*-

"""
The view of the hive-node and vault management.
"""
from flask_restful import Resource

from src.modules.provider.provider import Provider


class Vaults(Resource):
    def __init__(self):
        self.provider = Provider()

    def get(self):
        """ Get all vault information in this hive node.

        .. :quickref: 09 Provider; Get Vaults

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "vaults": [{
                    "pricing_using": <pricing name|str>,
                    "max_storage": <int>,
                    "file_use_storage": <int>,
                    "db_use_storage": <int>,
                    "user_did": <str>,
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        return self.provider.get_vaults()


class Backups(Resource):
    def __init__(self):
        self.provider = Provider()

    def get(self):
        """ Get all backup information in this hive node.

        .. :quickref: 09 Provider; Get Backups

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "backups": [{
                    "pricing_using": <pricing name|str>,
                    "max_storage": <int>,
                    "use_storage": <int>,
                    "user_did": <user did|str>,
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        return self.provider.get_backups()


class FilledOrders(Resource):
    def __init__(self):
        self.provider = Provider()

    def get(self):
        """ Get all payment information in this hive node.

        .. :quickref: 09 Provider; Get Payments

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "orders": [{
                    "order_id": <str>,
                    "receipt_id": <str>,
                    "user_did": <str>,
                    "subscription": <vault,backup|str>,
                    "pricing_name": <str>,
                    "ela_amount": <float>,
                    "ela_address": <str>,
                    "paid_did": <user did|str>,
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        return self.provider.get_filled_orders()
