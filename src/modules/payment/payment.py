# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
import traceback
import typing
from datetime import datetime

from flask import g

from src import hive_setting
from src.utils.http_exception import InvalidParameterException, BadRequestException, OrderNotFoundException, ReceiptNotFoundException
from src.utils.singleton import Singleton
from src.utils.payment_config import PaymentConfig
from src.modules.auth.auth import Auth
from src.modules.subscription.vault import VaultManager
from src.modules.backup.backup import BackupManager
from src.modules.payment.order import OrderManager, Order
from src.modules.payment.order_contract import OrderContract


class Payment(metaclass=Singleton):
    def __init__(self):
        self.ela_address = hive_setting.PAYMENT_RECEIVING_ADDRESS
        self.auth = Auth()
        self.vault_subscription = None
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
        """ :v2 API: """
        return {'version': PaymentConfig.get_version()}

    def place_order(self, subscription: str, pricing_name: str):
        """ Place a new order for upgrade user's vault.

        :param subscription vault/backup
        :param pricing_name the name of pricing package.

        :v2 API:
        """
        if subscription == Order.SUBSCRIPTION_VAULT:
            self.vault_manager.get_vault(g.usr_did)
            plan = PaymentConfig.get_vault_plan(pricing_name)
        else:
            self.backup_manager.get_backup(g.usr_did)
            plan = PaymentConfig.get_backup_plan(pricing_name)

        # plan must exist and not free
        if not plan or plan['amount'] <= 0.00000001:
            raise InvalidParameterException(f'Invalid pricing_name {pricing_name} or the related plan is free.')

        # create order with proof
        order = self.order_manager.insert_order(g.usr_did, subscription, plan)
        proof = self.auth.create_proof_for_order(g.usr_did, order.get_proof_details(), order.get_expire_time())
        self.order_manager.update_proof(order, proof)

        return order.to_place_order()

    def settle_order(self, contract_order_id: int):
        """ :v2 API: """
        # first step is to get the order information from contract
        try:
            order_info = self.order_contract.get_order(contract_order_id)
        except Exception as e:
            raise InvalidParameterException(f'Failed get order info from contract( maybe invalid order id '
                                            f'or the order not generated successfully ): {str(e)}, {traceback.format_exc()}')

        order = self.__verify_contract_order(order_info)

        # check the existence of the vault or backup, maybe removed by user :-(
        if order.get_subscription() == Order.SUBSCRIPTION_VAULT:
            self.vault_manager.get_vault(g.usr_did)
        else:
            self.backup_manager.get_backup(g.usr_did)

        # Upgrade vault or backup.
        order.set_contract_order_id(contract_order_id)
        self.order_manager.upgrade_vault_or_backup(g.usr_did, order)

        # Create a receipt.
        receipt = self.order_manager.insert_receipt(g.usr_did, order)
        receipt_proof = self.auth.create_receipt_proof_for_order(g.usr_did, order.get_receipt_proof_details(receipt))
        self.order_manager.update_receipt_proof(receipt, receipt_proof)

        # Update contract order id.
        self.order_manager.update_contract_order_id(order, contract_order_id)

        return receipt.to_settle_order()

    def __verify_contract_order(self, contract_order):
        if contract_order['to'] != self.ela_address:
            raise BadRequestException('The oder from order_id is not for this hive node.')

        # Make sure the proof is in this node.
        order = self.order_manager.get_order_by_proof(g.usr_did, contract_order['memo'])
        if order.is_settled():
            raise BadRequestException(f'The proof {contract_order["memo"]} invalid: the order has been settled.')

        if not order.belongs(g.usr_did):
            raise BadRequestException(f'The proof {contract_order["memo"]} invalid: not your order.')

        if not order.is_amount_enough(contract_order['amount']):
            raise BadRequestException(f'The proof {contract_order["memo"]} invalid: payment amount is not enough.')

        # Also needs to verify the proof.
        details, now = self.auth.get_proof_info(contract_order['memo'], g.usr_did), int(datetime.now().timestamp())
        if now > details['expiration_time']:
            raise BadRequestException(f'The proof {contract_order["memo"]} expired.')

        return order

    def get_orders(self, subscription: typing.Optional[str], contract_order_id: typing.Optional[int]):
        """ :v2 API: """
        orders = self.order_manager.get_orders(g.usr_did, subscription, contract_order_id)
        if not orders:
            raise OrderNotFoundException()
        return {
            'orders': [o.to_get_orders() for o in orders]
        }

    def get_receipts(self, contract_order_id: typing.Optional[int]):
        """ :v2 API: """
        receipts = self.order_manager.get_receipts(g.usr_did, contract_order_id)
        if not receipts:
            raise ReceiptNotFoundException()
        return {
            'receipts': [o.to_get_receipts() for o in receipts]
        }
