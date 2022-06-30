# -*- coding: utf-8 -*-

"""
The view of payment module.
"""
from flask_restful import Resource

from src.modules.payment.payment import Payment
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import RV


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
                "interim_orderid": "<ObjectId str>",  // internal order id on hive node
                "subscription": "vault",
                "pricing_plan": "Rookie",
                "paying_did": "did:elastos:iWFAUYhTa35c1f3335iCJvihZHx6q******",
                "payment_amount": 15,  // ELA
                "create_time": 1600073834,
                "expiration_time": 1755161834,
                "receiving_address": "0x60Dcc0f996963644102fC266b39F1116e5******",
                "state": "normal",
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
                        "paying_did": "did:elastos:iWFAUYhTa35c1f3335iCJvihZHx6q******",
                        "payment_amount": 14,  // ELA
                        "create_time": 1600073834,
                        "expiration_time": 1755161834,
                        "receiving_address": "0x60Dcc0f996963644102fC266b39F1116e*******",
                        "state": "normal",
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

            HTTP/1.1 404 Not Found

        """

        subscription = RV.get_body().get('subscription', str)
        pricing_name = RV.get_body().get('pricing_name', str)

        return self.payment.place_order(subscription, pricing_name)


class SettleOrder(Resource):
    def __init__(self):
        self.payment = Payment()

    def post(self, order_id):
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
                "receipt_id": “<ObjectId str>”,
                "order_id": 1234,
                "subscription": "vault",
                "pricing_plan": "Rookie",
                "payment_amount": "5",  // ELA
                "paid_did": "did:elastos:insTmxdDDuS9wHHfeYD1h5C2onEH******”,
                "create_time": 1600073834,
                "receiving_address": "912ec803b2ce49e4a541068d49******",
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
                        "pricing_plan": "Rookie",
                        "paid_did": "did:elastos:iWFAUYhTa35c1f3335iCJvihZHx6******",  // the did who paid for the order.
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

            HTTP/1.1 404 Not Found

        """

        contract_order_id = RV.get_value('order_id', order_id, int)

        return self.payment.settle_order(contract_order_id)


class Orders(Resource):
    def __init__(self):
        self.payment = Payment()

    def get(self):
        """ Get the orders for the vault or the backup service, or by specific order id.

        .. :quickref: 07 Payment; Get Orders

        **URL Parameters**:

        .. sourcecode:: http

            subscription: <vault | backup | all>    # optional
            order_id: <order_id>                    # optional

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
               "orders": [{
                    "order_id": 1234,
                    "subscription": "vault",
                    "pricing_plan": "Rookie",
                    "paying_did": "did:elastos:iWFAUYhTa35c1f3335iCJvihZHx6q******",
                    "payment_amount": "5",  // ELA
                    "create_time": 1600073834,
                    "expiration_time": 1755161834,
                    "receiving_address": "912ec803b2ce49e4a541068d49******",
                    "state": "paid",
                    "proof": "<jwt str>"
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        subscription = RV.get_args().get_opt('subscription', str, None)
        contract_order_id = RV.get_args().get_opt('order_id', int, None)

        if subscription and subscription not in ['vault', 'backup']:
            raise InvalidParameterException('Invalid parameter subscription: Can only be "vault" or "backup"')

        return self.payment.get_orders(subscription, contract_order_id)


class Receipts(Resource):
    def __init__(self):
        self.payment = Payment()

    def get(self):
        """ Get the receipt information by the order id.

        .. :quickref: 07 Payment; Get the Receipt

        **URL Parameters**:

        .. sourcecode:: http

            order_id: <order_id>  # optional

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "receipts": [{
                    "receipt_id": “<ObjectId str>”,
                    "order_id": 1234,
                    "subscription": "vault",
                    "pricing_plan": "Rookie",
                    "payment_amount": "5",  // ELA
                    "paid_did": "did:elastos:insTmxdDDuS9wHHfeYD1h5C2onEH******”,
                    "create_time": 1600073834,
                    "receiving_address": "912ec803b2ce49e4a541068d49******",
                    "receipt_proof": "<jwt str>"
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        contract_order_id = RV.get_args().get_opt('order_id', int, None)

        return self.payment.get_receipts(contract_order_id)
