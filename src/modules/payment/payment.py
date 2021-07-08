# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
from datetime import datetime

from hive.util.constants import DID_INFO_DB_NAME
from src.modules.auth.auth import Auth
from src.modules.scripting.scripting import validate_exists, check_auth
from src.modules.subscription.subscription import VaultSubscription
from src.utils.consts import COL_ORDERS, DID, APP_DID, COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, \
    COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_PROOF, CREATE_TIME, MODIFY_TIME
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
        subscription, plan = self.place_order_params_check(json_body)
        return self.create_order(did, app_did, subscription, plan)

    def place_order_params_check(self, json_body):
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

    def create_order(self, did, app_did, subscription, plan):
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
        pass

    @hive_restful_response
    def get_orders(self, subscription, order_id):
        pass

    @hive_restful_response
    def get_receipt_info(self, order_id):
        pass
