# -*- coding: utf-8 -*-

"""
The view of payment module.
"""
from flask import request
from flask_restful import Resource

from src.modules.payment.payment import Payment
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params


class Version(Resource):
    def __init__(self):
        self.payment = Payment()

    def get(self):
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
        return self.payment.get_version()


class PlaceOrder(Resource):
    def __init__(self):
        self.payment = Payment()

    def put(self):
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
               "order_id": "5f910273dc81b7a0b3f585fc",
               "subscription": "vault",
               "pricing_name": "Rookie",
               "ela_amount": 5.0,
               "ela_address": “912ec803b2ce49e4a541068d495ab570”,
               "proof": <jwt string>,
               "create_time":1626217349
            }

        the decoded content of proof is like this:

        .. code-block:: json

            {
               "header":{
                  "typ":"JWT",
                  "version":"1.0",
                  "alg":"ES256",
                  "kid": "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6q*****#primary", // service did
               },
               "payload":{
                  "ver":"1.0",
                  "sub":"Hive Payment",
                  "aud":"did:elastos:ixxxx", // the user who need to make payment
                  "iat":1600073832,
                  "iss":"did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6q*****", // service did
                  "interim_orderid":135, // internal order id on hive node
                  "order": {
                     "subscritpion":"vault/backup",
                     "pricing_plan":"rookie/advnced",
                     "payment_amount":14,
                     "create_time":1600073834,
                     "expiration_time":1755161834,
                     "receiving_address":"0x60Dcc0f996963644102fC266b39F1116e5df3333"
                  }
               },
               "signature":"rW6lGLpsGQJ7kojql78rX7p-MnBMBGEcBXYHkw_heisv7eEic574qL-0Immh0f0qFygNHY7RwhL47PDtFyNHAA\n"
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

        subscription, msg = params.get_str('subscription')
        if msg or subscription not in ['vault', 'backup']:
            raise InvalidParameterException(msg=msg)

        pricing_name, msg = params.get_str('pricing_name')
        if msg:
            raise InvalidParameterException(msg=msg)

        return self.payment.place_order(subscription, pricing_name)


class PayOrder(Resource):
    def __init__(self):
        self.payment = Payment()

    def post(self, order_id):
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
        return self.payment.pay_order(order_id, request.get_json(force=True, silent=True))


class Orders(Resource):
    def __init__(self):
        self.payment = Payment()

    def get(self):
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
        return self.payment.get_orders(subscription, order_id)


class ReceiptInfo(Resource):
    def __init__(self):
        self.payment = Payment()

    def get(self):
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
        return self.payment.get_receipt_info(request.args.get('order_id'))
