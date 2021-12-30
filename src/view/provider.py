# -*- coding: utf-8 -*-

"""
The view of the hive-node and vault management.
"""
from flask import Blueprint

from src.modules.provider.provider import Provider

blueprint = Blueprint('management', __name__)
provider: Provider = None


def init_app(app):
    """ This will be called by application initializer. """
    global provider
    provider = Provider()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/management/node/vaults', methods=['GET'])
def get_vaults():
    """ Get all vault information in this hive node.

    .. :quickref: 09 Management; Get Vaults

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

    return provider.get_vaults()


@blueprint.route('/api/v2/management/node/backups', methods=['GET'])
def get_backups():
    """ Get all backup information in this hive node.

    .. :quickref: 09 Management; Get Backups

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

    return provider.get_backups()


@blueprint.route('/api/v2/management/node/filled_orders', methods=['GET'])
def get_filled_orders():
    """ Get all payment information in this hive node.

    .. :quickref: 09 Management; Get Payments

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

    return provider.get_filled_orders()
