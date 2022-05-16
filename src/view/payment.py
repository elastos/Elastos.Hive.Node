# -*- coding: utf-8 -*-

"""
The view of payment module.
"""
from flask_restful import Resource

from src.modules.payment.payment import Payment
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params, rqargs


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
               "proof": "<jwt string>"
            }

        the decoded content of proof is like this:

        .. code-block:: json

            {
               "header":{
                    "typ": "JWT",
                    "version": "1.0",
                    "alg": "ES256",
               },
               "payload":{
                    "ver": "1.0",
                    "sub": "Hive Payment",
                    "aud": "did:elastos:ixxxx",  // the user who need to make payment
                    "iat": 1600073832,
                    "iss": "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6q*****",  // service did
                    "order": {
                        "interim_orderid": "<ObjectId str>",  // internal order id on hive node
                        "subscription": "vault/backup",
                        "pricing_plan": "rookie/advanced",
                        "payment_amount": 14,  // ELA
                        "create_time": 1600073834,
                        "expiration_time": 1755161834,
                        "receiving_address": "0x60Dcc0f996963644102fC266b39F1116e*******"
                    }
               },
               "signature": "rW6lGLpsGQJ7kojql78rX7p-MnBMBGEcBXYHkw_heisv7eEic574qL-0Immh0f0qFygNHY7RwhL47P*******"
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
            raise InvalidParameterException(msg='Invalid parameter "subscription"')

        pricing_name, msg = params.get_str('pricing_name')
        if msg:
            raise InvalidParameterException(msg=msg)

        return self.payment.place_order(subscription, pricing_name)


class SettleOrder(Resource):
    def __init__(self):
        self.payment = Payment()

    def post(self, contract_order_id):
        """ Notify the payment contract is already done and let hive node upgrade the user vault.

        After this, the vault will be upgraded for a specific pricing plan.

        .. :quickref: 07 Payment; Settle Order

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
               "receipt_proof": "<jwt str>"
            }

        the decoded content of receipt_proof is like this:

        .. code-block:: json

            {
                "header":{
                    "typ": "JWT",
                    "version": "1.0",
                    "alg": "ES256"
                },
                "payload":{
                    "ver": "1.0",
                    "sub": "Hive Recepit",
                    "aud": "did:elastos:ixxxx",  // the user who need to make payment
                    "iat": 1600073834,
                    "iss": "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6******",  // service did
                    "receipt":{
                        "receipt_id": "<ObjectId str>",
                        "order_id": 445,
                        "subscription": "vault",
                        "pricingPlan": "rookie",
                        "paying_did": "did:elastos:iWFAUYhTa35c1f3335iCJvihZHx6******",  // the did who paid for the order.
                        "payment_amount": 15,  // ELA
                        "create_time": 1600073834,
                        "receiving_address": "0x60Dcc0f996963644102fC266b39F1116******"
                    }
                },
                "signature": "rW6lGLpsGQJ7kojql78rX7p-MnBMBGEcBXYHkw_heisv7eEic574qL-0Immh0f0qFygNHY7RwhL47******"
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
        if not contract_order_id or not isinstance(contract_order_id, str) or not contract_order_id.isnumeric():
            raise InvalidParameterException('order_id must be number.')

        return self.payment.pay_order(int(contract_order_id))


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
                        "order_id": 1234,
                        "subscription": "vault",
                        "pricing_plan": "Rookie",
                        "payment_amount": "5",  // ELA
                        "create_time": 1600073834,
                        "expiration_time": 1755161834,
                        "receiving_address": "912ec803b2ce49e4a541068d49******",
                        "proof": "<jwt str>"
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
        subscription, msg = rqargs.get_str('subscription', None)
        if subscription is not None and subscription not in ['vault', 'backup']:
            raise InvalidParameterException(msg='Invalid parameter "subscription"')

        order_id, msg = rqargs.get_int('order_id', None)

        return self.payment.get_orders(subscription, order_id)


class Receipts(Resource):
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
                "receipt_id": “<ObjectId str>”,
                "order_id": 1234,
                "subscription": "vault",
                "pricing_plan": "Rookie",
                "payment_amount": "5",  // ELA
                "paid_did": "did:elastos:insTmxdDDuS9wHHfeYD1h5C2onEH******”,
                "create_time": 1600073834,
                "receiving_address": "912ec803b2ce49e4a541068d49******",
                "proof": "<jwt str>"
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
        order_id, msg = rqargs.get_int('order_id', None)
        if msg:
            raise InvalidParameterException(msg=msg)

        return self.payment.get_receipts(order_id)
