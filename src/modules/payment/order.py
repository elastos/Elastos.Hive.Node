import typing
from datetime import datetime

from bson import ObjectId

from src import hive_setting
from src.modules.database.mongodb_client import MongodbClient
from src.modules.subscription.backup import BackupManager
from src.modules.subscription.vault import VaultManager
from src.utils.consts import COL_ORDERS, COL_ORDERS_ELA_AMOUNT, COL_ORDERS_PROOF, USR_DID, COL_ORDERS_CONTRACT_ORDER_ID, COL_ORDERS_SUBSCRIPTION, VERSION, \
    COL_ORDERS_PRICING_NAME, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_STATUS, COL_ORDERS_STATUS_NORMAL, COL_RECEIPTS_ORDER_ID, COL_RECEIPTS_TRANSACTION_ID, \
    COL_RECEIPTS_PAID_DID, COL_RECEIPTS
from src.utils.http_exception import OrderNotFoundException
from src.utils_v1.payment.payment_config import PaymentConfig


class Receipt:
    def __init__(self, doc):
        self.doc = doc

    def get_id(self) -> typing.Optional[ObjectId]:
        return self.doc['_id']


class Order:
    SUBSCRIPTION_VAULT = 'vault'
    SUBSCRIPTION_BACKUP = 'backup'

    def __init__(self, doc):
        self.doc = doc

    def get_id(self) -> typing.Optional[ObjectId]:
        return self.doc['_id']

    def get_plan(self) -> typing.Optional[dict]:
        name = self.doc[COL_ORDERS_PRICING_NAME]
        return PaymentConfig.get_pricing_plan(name) if self.is_for_vault() else PaymentConfig.get_backup_plan(name)

    def is_for_vault(self):
        return self.doc[COL_ORDERS_SUBSCRIPTION] == Order.SUBSCRIPTION_VAULT

    def is_amount_enough(self, amount):
        return amount - self.doc[COL_ORDERS_ELA_AMOUNT] > -0.01

    def belongs(self, user_did):
        return user_did == self.doc[USR_DID]

    def is_settled(self):
        return self.doc[COL_ORDERS_CONTRACT_ORDER_ID] is not None

    def get_proof_details(self):
        now = int(datetime.utcnow().timestamp())
        exp = now + 7 * 24 * 3600
        return {
            "interim_orderid": str(self.doc['_id']),
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "create_time": now,
            "expiration_time": exp,
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS]
        }, exp

    def get_receipt_proof_details(self, receipt: Receipt):
        return {
            "receipt_id": str(receipt.get_id()),
            "order_id": self.doc[COL_ORDERS_CONTRACT_ORDER_ID],
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "paying_did": self.doc[USR_DID],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "create_time": int(datetime.utcnow().timestamp()),
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS]
        }


class OrderManager:
    def __init__(self):
        self.ela_address = hive_setting.PAYMENT_ADDRESS
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()
        self.backup_manager = BackupManager()

    def get_order(self, order_id):
        """ get by internal id """
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc = col.find_one({'_id': ObjectId(order_id)})
        if not doc:
            raise OrderNotFoundException()
        return Order(doc)

    def get_order_by_proof(self, proof: str):
        """ get by internal id """
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc = col.find_one({COL_ORDERS_PROOF: proof})
        if not doc:
            raise OrderNotFoundException()
        return Order(doc)

    def insert_order(self, user_did, subscription: str, plan: dict):
        doc = {
            USR_DID: user_did,
            COL_ORDERS_SUBSCRIPTION: subscription,
            VERSION: PaymentConfig.get_all_package_info().get('version', '1.0'),
            COL_ORDERS_PRICING_NAME: plan['name'],
            COL_ORDERS_ELA_AMOUNT: plan['amount'],
            COL_ORDERS_ELA_ADDRESS: self.ela_address,
            COL_ORDERS_PROOF: None,
            COL_ORDERS_CONTRACT_ORDER_ID: None
        }
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc['_id'] = col.insert_one(doc)['inserted_id']
        return Order(doc)

    def update_proof(self, order: Order, proof: str):
        col = self.mcli.get_management_collection(COL_ORDERS)
        col.update_one({'_id': order.get_id()}, {'$set': {COL_ORDERS_PROOF: proof}})

    def update_contract_order_id(self, order: Order, contract_order_id: int):
        col = self.mcli.get_management_collection(COL_ORDERS)
        col.update_one({'_id': order.get_id()}, {'$set': {COL_ORDERS_CONTRACT_ORDER_ID: contract_order_id}})

    def update_receipt_proof(self, receipt: Receipt, receipt_proof: str):
        col = self.mcli.get_management_collection(COL_RECEIPTS)
        col.update_one({'_id': receipt.get_id()}, {'$set': {COL_ORDERS_PROOF: receipt_proof}})

    def insert_receipt(self, user_did, order: Order):
        receipt = {
            USR_DID: user_did,
            COL_RECEIPTS_ORDER_ID: str(order.get_id()),
            COL_RECEIPTS_PAID_DID: user_did,
            COL_ORDERS_PROOF: ''
        }
        col = self.mcli.get_management_collection(COL_RECEIPTS)
        receipt['_id'] = col.insert_one(receipt)['inserted_id']
        return Receipt(receipt)

    def upgrade_vault_or_backup(self, user_did, order: Order):
        plan = order.get_plan()
        if order.is_for_vault():
            self.vault_manager.upgrade(user_did, plan)
        else:
            self.backup_manager.upgrade(user_did, plan)

