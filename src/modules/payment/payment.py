# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
from datetime import datetime

from bson import ObjectId

from hive.util.constants import DID_INFO_DB_NAME
from src.modules.auth.auth import Auth
from src.modules.scripting.scripting import validate_exists, check_auth
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import COL_ORDERS, DID, APP_DID, COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, \
    COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_PROOF, CREATE_TIME, MODIFY_TIME, \
    COL_RECEIPTS_ID, COL_RECEIPTS_ORDER_ID, COL_RECEIPTS_TRANSACTION_ID, COL_RECEIPTS_PAID_DID, COL_RECEIPTS
from src.utils.db_client import cli
from src.utils.http_exception import InvalidParameterException
from src.utils.http_response import hive_restful_response


class Payment:
    def __init__(self, app, hive_setting):
        self.vault_subscription = VaultSubscription()
        self.ela_address = hive_setting.HIVE_PAYMENT_ADDRESS
        self.auth = Auth(app, hive_setting)

    @hive_restful_response
    def get_version(self):
        return {'version': self.vault_subscription.get_price_plans_version()}

    @hive_restful_response
    def place_order(self, json_body):
        did, app_did = check_auth()
        subscription, plan = self._place_order_params_check(json_body)
        return self._create_order(did, app_did, subscription, plan)

    def _place_order_params_check(self, json_body):
        if not json_body:
            raise InvalidParameterException(msg='Request body should not empty.')
        validate_exists(json_body, '', ('subscription', 'pricing_name'))

        subscription, pricing_name = json_body.get('subscription', None), json_body.get('pricing_name', None)
        if subscription not in ('vault', 'backup'):
            raise InvalidParameterException(msg=f'Invalid subscription: {subscription}.')

        plan = self.vault_subscription.get_price_plan(subscription, pricing_name)
        if not plan:
            raise InvalidParameterException(msg=f'Invalid pricing_name: {pricing_name}.')

        return subscription, plan

    def _create_order(self, did, app_did, subscription, plan):
        now = datetime.utcnow().timestamp()
        doc = {
            DID: did,
            APP_DID: app_did,
            COL_ORDERS_SUBSCRIPTION: subscription,
            COL_ORDERS_PRICING_NAME: plan['name'],
            COL_ORDERS_ELA_AMOUNT: plan['amount'],
            COL_ORDERS_ELA_ADDRESS: self.ela_address,
            COL_ORDERS_PROOF: self.auth.create_order_proof(did),
            CREATE_TIME: now,
            MODIFY_TIME: now
        }
        res = cli.insert_one_origin(DID_INFO_DB_NAME, COL_ORDERS, doc, is_create=True, is_extra=False)
        doc['order_id'] = res['inserted_id']
        return {k: doc[k] for k in doc.keys() if k in ['order_id',
                                                       COL_ORDERS_SUBSCRIPTION,
                                                       COL_ORDERS_PRICING_NAME,
                                                       COL_ORDERS_ELA_AMOUNT,
                                                       COL_ORDERS_ELA_ADDRESS,
                                                       COL_ORDERS_PROOF]}

    @hive_restful_response
    def pay_order(self, order_id, json_body):
        did, app_did = check_auth()
        order, transaction_id, paid_did = self._check_pay_order_params(did, app_did, order_id, json_body)
        receipt = self._update_transaction_id(did, app_did, order, transaction_id, paid_did)
        return {
            COL_RECEIPTS_ID: receipt['id'],
            COL_RECEIPTS_ORDER_ID: str(order['_id']),
            COL_RECEIPTS_TRANSACTION_ID: transaction_id,
            COL_ORDERS_PRICING_NAME: order[COL_ORDERS_PRICING_NAME],
            COL_RECEIPTS_PAID_DID: receipt[COL_RECEIPTS_PAID_DID],
            COL_ORDERS_ELA_AMOUNT: order[COL_ORDERS_ELA_AMOUNT],
            COL_ORDERS_PROOF: order[COL_ORDERS_PROOF]
        }

    def _check_pay_order_params(self, did, app_did, order_id, json_body):
        if not order_id:
            raise InvalidParameterException(msg='Order id MUST be provided.')

        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_ORDERS, {'_id': ObjectId(order_id)}, is_raise=False)
        if not doc or doc[DID] != did or doc[APP_DID] != app_did:
            raise InvalidParameterException(msg='Order id is invalid.')

        if not json_body:
            raise InvalidParameterException(msg='Request body should not empty.')
        validate_exists(json_body, '', 'transaction_id')

        transaction_id = json_body.get('transaction_id', None)
        paid_did = self._check_transaction_id(doc, transaction_id)
        return doc, transaction_id, paid_did

    def _check_transaction_id(self, doc, transaction_id):
        # TODO: verify the transaction id online.
        return None

    def _update_transaction_id(self, did, app_did, order, transaction_id, paid_did):
        now = datetime.utcnow().timestamp()
        receipt = {
            DID: did,
            APP_DID: app_did,
            COL_RECEIPTS_ORDER_ID: str(order['_id']),
            COL_RECEIPTS_TRANSACTION_ID: transaction_id,
            COL_RECEIPTS_PAID_DID: paid_did,
            CREATE_TIME: now,
            MODIFY_TIME: now
        }
        res = cli.insert_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, receipt, is_create=True, is_extra=False)
        receipt['id'] = res['inserted_id']
        return receipt

    @hive_restful_response
    def get_orders(self, subscription, order_id):
        pass

    @hive_restful_response
    def get_receipt_info(self, order_id):
        pass
