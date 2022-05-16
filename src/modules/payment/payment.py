# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
import traceback
from datetime import datetime

from bson import ObjectId
from flask import g

from src import hive_setting
from src.modules.payment.order import OrderManager, Order
from src.modules.payment.order_contract import OrderContract
from src.modules.subscription.backup import BackupManager
from src.modules.subscription.vault import VaultManager
from src.utils_v1.constants import DID_INFO_DB_NAME
from src.modules.auth.auth import Auth
from src.utils.consts import COL_ORDERS, COL_ORDERS_SUBSCRIPTION, COL_ORDERS_PRICING_NAME, \
    COL_ORDERS_ELA_AMOUNT, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_PROOF, CREATE_TIME, MODIFY_TIME, \
    COL_RECEIPTS_ID, COL_RECEIPTS_ORDER_ID, COL_RECEIPTS_TRANSACTION_ID, COL_RECEIPTS_PAID_DID, COL_RECEIPTS, \
    COL_ORDERS_STATUS, COL_ORDERS_STATUS_NORMAL, COL_ORDERS_STATUS_ARCHIVE, USR_DID
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
        self.vault_manager = VaultManager()
        self.backup_manager = BackupManager()
        self.order_contract = OrderContract()
        self.order_manager = OrderManager()

    def _get_vault_subscription(self):
        if not self.vault_subscription:
            from src.modules.subscription.subscription import VaultSubscription
            self.vault_subscription = VaultSubscription()
        return self.vault_subscription

    def get_version(self):
        return {'version': self._get_vault_subscription().get_price_plans_version()}

    def place_order(self, subscription: str, pricing_name: str):
        """ Place a new order for upgrade user's vault.

        :param subscription vault/backup
        :param pricing_name the name of pricing package.

        :v2 API:
        """
        if subscription == Order.SUBSCRIPTION_VAULT:
            self.vault_manager.get_vault(g.usr_did)
            plan = PaymentConfig.get_pricing_plan(pricing_name)
        else:
            self.backup_manager.get_backup(g.usr_did)
            plan = PaymentConfig.get_backup_plan(pricing_name)

        # plan must exist and not free
        if not plan or plan['amount'] <= 0.01:
            raise InvalidParameterException(msg=f'Invalid pricing_name {pricing_name} or the related plan is free.')

        # create order with proof
        order = self.order_manager.insert_order(g.usr_did, subscription, plan)
        proof = self.auth.create_proof_for_order(g.usr_did, *order.get_proof_details())
        self.order_manager.update_proof(order, proof)

        return {
            'proof': proof
        }

    def pay_order(self, contract_order_id: int):
        """ :v2 API: """
        try:
            order_info = self.order_contract.get_order(contract_order_id)
        except Exception as e:
            raise BadRequestException(msg=f'Failed get order info from contract: {str(e)}, {traceback.format_exc()}')

        if not order_info:
            raise BadRequestException(msg=f'Not found order info by order id.')

        order = self.__verify_contract_order(order_info)

        # Upgrade vault or backup.
        self.order_manager.upgrade_vault_or_backup(g.usr_did, order)

        # Create a receipt.
        receipt = self.order_manager.insert_receipt(g.usr_did, order)
        receipt_proof = self.auth.create_receipt_proof_for_order(g.usr_did, order.get_receipt_proof_details(receipt))
        self.order_manager.update_receipt_proof(receipt, receipt_proof)

        # Update contract order id.
        self.order_manager.update_contract_order_id(order, contract_order_id)

        return {
            'receipt_proof': receipt_proof
        }

    def __verify_contract_order(self, contract_order):
        # Make sure the proof is in this node.
        order = self.order_manager.get_order_by_proof(contract_order['memo'])
        if order.is_settled():
            raise BadRequestException(msg=f'The proof {contract_order["memo"]} invalid: the order has been settled.')

        if not order.belongs(g.usr_did):
            raise BadRequestException(msg=f'The proof {contract_order["memo"]} invalid: not your order.')

        if not order.is_amount_enough(contract_order['amount']):
            raise BadRequestException(msg=f'The proof {contract_order["memo"]} invalid: payment amount is not enough.')

        # Also needs to verify the proof.
        details, now = self.auth.get_proof_info(contract_order['memo'], g.usr_did), int(datetime.utcnow().timestamp())
        if now > details['expiration_time']:
            raise BadRequestException(msg=f'The proof {contract_order["memo"]} expired.')

        return order

    def get_orders(self, subscription, order_id):
        """ :v2 API: """
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
        order = self.__check_param_order_id(g.usr_did, order_id)
        receipt = cli.find_one_origin(DID_INFO_DB_NAME, COL_RECEIPTS,
                                      {COL_RECEIPTS_ORDER_ID: order_id}, throw_exception=False)
        if not receipt:
            raise ReceiptNotFoundException(msg='Receipt can not be found by order_id.')
        return self.__get_receipt_vo(order, receipt)

    def __check_param_order_id(self, user_did, order_id, is_pay_order=False):
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

    def __get_receipt_vo(self, order, receipt):
        return {
            COL_RECEIPTS_ID: str(receipt['_id']),
            COL_RECEIPTS_ORDER_ID: str(order['_id']),
            COL_RECEIPTS_TRANSACTION_ID: receipt[COL_RECEIPTS_TRANSACTION_ID],
            COL_ORDERS_PRICING_NAME: order[COL_ORDERS_PRICING_NAME],
            COL_RECEIPTS_PAID_DID: receipt[COL_RECEIPTS_PAID_DID],
            COL_ORDERS_ELA_AMOUNT: order[COL_ORDERS_ELA_AMOUNT],
            COL_ORDERS_PROOF: order[COL_ORDERS_PROOF]
        }

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
