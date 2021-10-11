# -*- coding: utf-8 -*-

"""
The view of payment module.
"""
from flask import Blueprint, request

from src.modules.payment.payment import Payment

blueprint = Blueprint('payment', __name__)
payment: Payment = Payment()


def init_app(app):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/payment/version', methods=['GET'])
def get_version():
    """ Get the version of the payment implementation.

    .. :quickref: 07 Payment; Get Version

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "version": "1.0"
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    """
    return payment.get_version()


@blueprint.route('/api/v2/payment/order', methods=['PUT'])
def place_order():
    """ Place an order for getting more storage space.
    The vault service MUST be subscribed before placing the order.

    .. :quickref: 07 Payment; Place Order

    **Request**:

    .. sourcecode:: http

        {
           "subscription": <vault | backup>,
           "pricing_name": "Rookie"
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
           "order_id":"5f910273dc81b7a0b3f585fc",
           "subscription":"vault",
           "pricing_name":"Rookie",
           "ela_amount":5.0,
           "ela_address":“912ec803b2ce49e4a541068d495ab570”,
           "proof":“d444f18dc350fb334c811d9c4b0dfdf63f67df47”,
           "create_time":1626217349
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
    return payment.place_order(request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/payment/order/<order_id>', methods=['POST'])
def pay_order(order_id):
    """ Pay for the order placed before with payment transaction id.
    After this, the vault will be upgraded for a specific pricing plan.

    .. :quickref: 07 Payment; Pay the Order

    **Request**:

    .. sourcecode:: http

        {
           "transaction_id":“a677abfcc88c8126deedd719202e5092”
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
           "receipt_id": "8f0e7a8a0ebe84271e079889c9c9b8b3",
           "order_id": "912ec803b2ce49e4a541068d495ab570",
           "transaction_id": "a677abfcc88c8126deedd719202e5092",
           "pricing_name": "Rookie",
           "paid_did": "did:elastos:insTmxdDDuS9wHHfeYD1h5C2onEHh3D8Vq",
           "ela_amount": "5",
           "proof": "d444f18dc350fb334c811d9c4b0dfdf63f67df47"
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
    return payment.pay_order(order_id, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/payment/order', methods=['GET'])
def get_orders():
    """ Get the orders for the vault or the backup service, or by specific order id.

    .. :quickref: 07 Payment; Get Orders

    **URL Parameters**:

    .. sourcecode:: http

        subscription: <vault | backup | all>
        order_id: <order_id>

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
           "orders":[
              {
                 "order_id": "5f910273dc81b7a0b3f585fc",
                 "subscription": "vault",
                 "pricing_name": "Rookie",
                 "ela_amount": "5",
                 "ela_address": "912ec803b2ce49e4a541068d495ab570",
                 "proof": "d444f18dc350fb334c811d9c4b0dfdf63f67df47",
                 "create_time": 1626217349
              }
           ]
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
    subscription, order_id = request.args.get('subscription'), request.args.get('order_id')
    return payment.get_orders(subscription, order_id)


@blueprint.route('/api/v2/payment/receipt', methods=['GET'])
def get_receipt_info():
    """ Get the receipt information by the order id.

    .. :quickref: 07 Payment; Get the Receipt

    **URL Parameters**:

    .. sourcecode:: http

        order_id: <order_id>

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "receipt_id": “8f0e7a8a0ebe84271e079889c9c9b8b3”,
            "order_id": “912ec803b2ce49e4a541068d495ab570”,
            "transaction_id": “a677abfcc88c8126deedd719202e5092”,
            "pricing_name": "Rookie",
            "paid_did": "did:elastos:insTmxdDDuS9wHHfeYD1h5C2onEHh3D8Vq”,
            "ela_amount": “5”,
            "proof": "d444f18dc350fb334c811d9c4b0dfdf63f67df47”
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
    return payment.get_receipt_info(request.args.get('order_id'))
