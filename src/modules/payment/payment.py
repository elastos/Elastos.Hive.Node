# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
import json
from datetime import datetime

from bson import ObjectId
from flask import g

from src import hive_setting
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_ACCESS_R
from src.modules.auth.auth import Auth
from src.modules.scripting.scripting import validate_exists
from src.utils.consts import COL_ORDERS, COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, \
    COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_PROOF, CREATE_TIME, MODIFY_TIME, \
    COL_RECEIPTS_ID, COL_RECEIPTS_ORDER_ID, COL_RECEIPTS_TRANSACTION_ID, COL_RECEIPTS_PAID_DID, COL_RECEIPTS, \
    COL_ORDERS_STATUS, COL_ORDERS_STATUS_NORMAL, COL_ORDERS_STATUS_ARCHIVE, COL_ORDERS_STATUS_PAID, USR_DID
from src.utils.db_client import cli
from src.utils.http_exception import InvalidParameterException, BadRequestException, OrderNotFoundException, \
    ReceiptNotFoundException
from src.utils.resolver import ElaResolver
from src.utils.singleton import Singleton
from src.utils_v1.payment.payment_config import PaymentConfig


class Payment(metaclass=Singleton):
    def __init__(self):
        self.ela_address = hive_setting.PAYMENT_ADDRESS
        PaymentConfig.init_config()
        self.auth = Auth()
        self.vault_subscription = None
        self.ela_resolver = ElaResolver(hive_setting.ESC_RESOLVER_URL)

    def _get_vault_subscription(self):
        if not self.vault_subscription:
            from src.modules.subscription.subscription import VaultSubscription
            self.vault_subscription = VaultSubscription()
        return self.vault_subscription

    def get_version(self):
        return {'version': self._get_vault_subscription().get_price_plans_version()}

    def place_order(self, json_body):
        cli.check_vault_access(g.usr_did, VAULT_ACCESS_R)
        subscription, plan = self._check_place_order_params(json_body)
        return self._get_order_vo(self._create_order(g.usr_did, subscription, plan))

    def _check_place_order_params(self, json_body):
        if not json_body:
            raise InvalidParameterException(msg='Request body should not empty.')
        validate_exists(json_body, '', ('subscription', 'pricing_name'))

        subscription, pricing_name = json_body.get('subscription', None), json_body.get('pricing_name', None)
        if subscription not in ('vault', 'backup'):
            raise InvalidParameterException(msg=f'Invalid subscription: {subscription}.')

        plan = self._get_vault_subscription().get_price_plan(subscription, pricing_name)
        if not plan:
            raise InvalidParameterException(msg=f'Invalid pricing_name: {pricing_name}.')

        if plan['amount'] <= 0:
            raise InvalidParameterException(msg=f'Invalid pricing_name which is free.')

        return subscription, plan

    def _create_order(self, user_did, subscription, plan):
        doc = {
            USR_DID: user_did,
            COL_ORDERS_SUBSCRIPTION: subscription,
            COL_ORDERS_PRICING_NAME: plan['name'],
            COL_ORDERS_ELA_AMOUNT: plan['amount'],
            COL_ORDERS_ELA_ADDRESS: self.ela_address,
            COL_ORDERS_PROOF: '',
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_NORMAL
        }

        res = cli.insert_one_origin(DID_INFO_DB_NAME, COL_ORDERS, doc, create_on_absence=True)

        doc['_id'] = res['inserted_id']
        doc[COL_ORDERS_PROOF] = self.auth.create_order_proof(user_did, doc['_id'])
        cli.update_one_origin(DID_INFO_DB_NAME, COL_ORDERS, {'_id': ObjectId(doc['_id'])},
                              {'$set': {COL_ORDERS_PROOF: doc[COL_ORDERS_PROOF]}}, is_extra=True)

        return doc

    def _get_order_vo(self, order):
        return {
            'order_id': str(order['_id']),
            COL_ORDERS_SUBSCRIPTION: order[COL_ORDERS_SUBSCRIPTION],
            COL_ORDERS_PRICING_NAME: order[COL_ORDERS_PRICING_NAME],
            COL_ORDERS_ELA_AMOUNT: order[COL_ORDERS_ELA_AMOUNT],
            COL_ORDERS_ELA_ADDRESS: order[COL_ORDERS_ELA_ADDRESS],
            COL_ORDERS_PROOF: order[COL_ORDERS_PROOF],
            CREATE_TIME: int(order[CREATE_TIME]),
        }

    def pay_order(self, order_id, json_body):
        vault = self._get_vault_subscription().get_checked_vault(g.usr_did)

        order, transaction_id, paid_did = self._check_pay_order_params(g.usr_did, order_id, json_body)

        receipt = self._create_receipt(g.usr_did, order, transaction_id, paid_did)
        self._update_order_status(str(order['_id']), COL_ORDERS_STATUS_PAID)
        self._get_vault_subscription().upgrade_vault_plan(g.usr_did, vault, order[COL_ORDERS_PRICING_NAME])
        return self._get_receipt_vo(order, receipt)

    def _update_order_status(self, order_id, status):
        update = {
            COL_ORDERS_STATUS: status,
            MODIFY_TIME: datetime.utcnow().timestamp(),
        }
        cli.update_one_origin(DID_INFO_DB_NAME, COL_ORDERS, {'_id': ObjectId(order_id)}, {'$set': update},
                              is_extra=True)

    def _get_receipt_vo(self, order, receipt):
        return {
            COL_RECEIPTS_ID: str(receipt['_id']),
            COL_RECEIPTS_ORDER_ID: str(order['_id']),
            COL_RECEIPTS_TRANSACTION_ID: receipt[COL_RECEIPTS_TRANSACTION_ID],
            COL_ORDERS_PRICING_NAME: order[COL_ORDERS_PRICING_NAME],
            COL_RECEIPTS_PAID_DID: receipt[COL_RECEIPTS_PAID_DID],
            COL_ORDERS_ELA_AMOUNT: order[COL_ORDERS_ELA_AMOUNT],
            COL_ORDERS_PROOF: order[COL_ORDERS_PROOF]
        }

    def _check_pay_order_params(self, user_did, order_id, json_body):
        order = self._check_param_order_id(user_did, order_id, is_pay_order=True)
        if not json_body:
            raise InvalidParameterException(msg='Request body should not empty.')
        validate_exists(json_body, '', ['transaction_id', ])

        transaction_id = json_body.get('transaction_id', None)
        paid_did = self._check_transaction_id(user_did, order, transaction_id)
        return order, transaction_id, paid_did

    def _check_param_order_id(self, user_did, order_id, is_pay_order=False):
        if not order_id:
            raise InvalidParameterException(msg='Order id MUST be provided.')

        col_filter = {'_id': ObjectId(order_id), USR_DID: user_did}
        if is_pay_order:
            col_filter[COL_ORDERS_STATUS] = COL_ORDERS_STATUS_NORMAL
        order = cli.find_one_origin(DID_INFO_DB_NAME, COL_ORDERS, col_filter, throw_exception=False)
        if not order:
            raise InvalidParameterException(msg='Order id is invalid because of not finding the order.')

        if is_pay_order:
            receipt = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS,
                                          {COL_RECEIPTS_ORDER_ID: order_id}, throw_exception=False)
            if receipt:
                raise InvalidParameterException(msg='Order id is invalid because of existing the relating receipt.')

        return order

    def _check_transaction_id(self, user_did, order, transaction_id):
        # INFO: do not need local check because of binding order_id
        # self._check_transaction_id_local(transaction_id)
        self._check_transaction_id_remote(user_did, order, transaction_id)
        return user_did

    def _check_transaction_id_local(self, transaction_id):
        receipt = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS,
                                      {COL_RECEIPTS_TRANSACTION_ID: transaction_id}, throw_exception=False)
        if receipt:
            raise InvalidParameterException(msg=f'Transaction id {transaction_id} has already been used.')

    def _check_transaction_id_remote(self, user_did, order, transaction_id):
        result = self.ela_resolver.get_transaction_info(transaction_id)
        # INFO: this is used to check whether the transaction is on block chain.
        if result['time'] < 1:
            raise BadRequestException(msg='invalid transaction id with result time abnormal')
        proof = self._get_proof_by_result(result)
        self.auth.verify_order_proof(proof, user_did, str(order['_id']))
        amount, address = float(result['vout'][0]['value']), result['vout'][0]['address']
        if amount - order[COL_ORDERS_ELA_AMOUNT] < -0.01 or order[COL_ORDERS_ELA_ADDRESS] != address:
            raise BadRequestException(msg='invalid transaction id with no more amount or invalid address')

    def _get_proof_by_result(self, result):
        try:
            memo = result['attributes'][0]['data']
            json_memo = json.loads(self.ela_resolver.hexstring_to_bytes(memo, reverse=False).decode('utf-8'))
            if not isinstance(json_memo, dict) or json_memo.get('source') != 'hive node':
                raise BadRequestException(msg='invalid transaction id with invalid memo type')
            return json_memo.get('proof')
        except Exception as e:
            raise BadRequestException(msg=f'invalid transaction id with invalid memo: {str(e)}')

    def _create_receipt(self, user_did, order, transaction_id, paid_did):
        now = datetime.utcnow().timestamp()
        receipt = {
            USR_DID: user_did,
            COL_RECEIPTS_ORDER_ID: str(order['_id']),
            COL_RECEIPTS_TRANSACTION_ID: transaction_id,
            COL_RECEIPTS_PAID_DID: paid_did,
            COL_ORDERS_PROOF: '',
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_NORMAL
        }
        res = cli.insert_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, receipt, create_on_absence=True)

        receipt['_id'] = res['inserted_id']
        receipt[COL_ORDERS_PROOF] = self.auth.create_order_proof(
            user_did, receipt['_id'], amount=order[COL_ORDERS_ELA_AMOUNT], is_receipt=True)
        cli.update_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {'_id': ObjectId(receipt['_id'])},
                              {'$set': {COL_ORDERS_PROOF: receipt[COL_ORDERS_PROOF]}}, is_extra=True)
        return receipt

    def get_orders(self, subscription, order_id):
        if subscription not in ('vault', 'backup'):
            raise InvalidParameterException(msg=f'Invalid subscription: {subscription}.')

        col_filter = {}
        if subscription:
            col_filter[COL_ORDERS_SUBSCRIPTION] = subscription
        if order_id:
            col_filter[COL_RECEIPTS_ORDER_ID] = order_id
        orders = cli.find_many_origin(DID_INFO_DB_NAME, COL_ORDERS, col_filter, throw_exception=False)
        if not orders:
            raise OrderNotFoundException(msg='Can not get the matched orders.')
        return {'orders': list(map(lambda o: {'order_id': str(o['_id']),
                                              COL_ORDERS_SUBSCRIPTION: o[COL_ORDERS_SUBSCRIPTION],
                                              COL_ORDERS_PRICING_NAME: o[COL_ORDERS_PRICING_NAME],
                                              COL_ORDERS_ELA_AMOUNT: o[COL_ORDERS_ELA_AMOUNT],
                                              COL_ORDERS_ELA_ADDRESS: o[COL_ORDERS_ELA_ADDRESS],
                                              COL_ORDERS_PROOF: o[COL_ORDERS_PROOF],
                                              COL_ORDERS_STATUS: o[COL_ORDERS_STATUS],
                                              CREATE_TIME: int(o[CREATE_TIME])}, orders))}

    def get_receipt_info(self, order_id):
        order = self._check_param_order_id(g.usr_did, order_id)
        receipt = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS,
                                      {COL_RECEIPTS_ORDER_ID: order_id}, throw_exception=False)
        if not receipt:
            raise ReceiptNotFoundException(msg='Receipt can not be found by order_id.')
        return self._get_receipt_vo(order, receipt)

    def archive_orders(self, user_did):
        """ for unsubscribe the vault """
        update = {
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_ARCHIVE,
            MODIFY_TIME: datetime.utcnow().timestamp(),
        }
        if cli.is_col_exists(DID_INFO_DB_NAME, COL_ORDERS):
            cli.update_one_origin(DID_INFO_DB_NAME, COL_ORDERS, {USR_DID: user_did}, {'$set': update},
                                  is_many=True, is_extra=True)
        if cli.is_col_exists(DID_INFO_DB_NAME, COL_RECEIPTS):
            cli.update_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS, {USR_DID: user_did}, {'$set': update},
                                  is_many=True, is_extra=True)
