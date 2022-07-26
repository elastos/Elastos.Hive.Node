import typing as t
from datetime import datetime

from bson import ObjectId

from src import hive_setting
from src.utils.consts import COL_ORDERS, COL_ORDERS_ELA_AMOUNT, COL_ORDERS_PROOF, USR_DID, COL_ORDERS_CONTRACT_ORDER_ID, COL_ORDERS_SUBSCRIPTION, VERSION, \
    COL_ORDERS_PRICING_NAME, COL_ORDERS_ELA_ADDRESS, COL_ORDERS_STATUS, COL_ORDERS_STATUS_NORMAL, COL_RECEIPTS_ORDER_ID, \
    COL_RECEIPTS_PAID_DID, COL_RECEIPTS, COL_ORDERS_EXPIRE_TIME, COL_ORDERS_STATUS_PAID, COL_ORDERS_STATUS_ARCHIVE, COL_ORDERS_STATUS_EXPIRED
from src.utils.http_exception import OrderNotFoundException
from src.utils_v1.payment.payment_config import PaymentConfig
from src.modules.database.mongodb_client import MongodbClient
from src.modules.subscription.vault import VaultManager
from src.modules.subscription.backup import BackupManager


class Receipt:
    def __init__(self, doc):
        self.doc = doc

    def get_id(self) -> t.Optional[ObjectId]:
        return self.doc['_id']

    def set_proof(self, proof):
        self.doc[COL_ORDERS_PROOF] = proof

    def to_settle_order(self):
        return self.to_get_receipts()

    def to_get_receipts(self):
        """ for the response of API """
        return {
            "receipt_id": str(self.get_id()),
            "order_id": self.doc[COL_ORDERS_CONTRACT_ORDER_ID],
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "paid_did": self.doc[COL_RECEIPTS_PAID_DID],
            "create_time": self.doc['created'],
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS],
            "receipt_proof": self.doc[COL_ORDERS_PROOF]
        }


class Order:
    SUBSCRIPTION_VAULT = 'vault'
    SUBSCRIPTION_BACKUP = 'backup'

    def __init__(self, doc):
        self.doc = doc

    def get_id(self) -> t.Optional[ObjectId]:
        return self.doc['_id']

    def get_plan(self) -> t.Optional[dict]:
        name = self.doc[COL_ORDERS_PRICING_NAME]
        return PaymentConfig.get_pricing_plan(name) if self.is_for_vault() else PaymentConfig.get_backup_plan(name)

    def set_contract_order_id(self, contract_order_id):
        self.doc[COL_ORDERS_CONTRACT_ORDER_ID] = contract_order_id

    def get_contract_order_id(self):
        return self.doc[COL_ORDERS_CONTRACT_ORDER_ID]

    def get_expire_time(self):
        return self.doc[COL_ORDERS_EXPIRE_TIME]

    def get_subscription(self):
        return self.doc[COL_ORDERS_SUBSCRIPTION]

    def get_amount(self):
        return self.doc[COL_ORDERS_ELA_AMOUNT]

    def get_receiving_address(self):
        return self.doc[COL_ORDERS_ELA_ADDRESS]

    def is_for_vault(self):
        return self.doc[COL_ORDERS_SUBSCRIPTION] == Order.SUBSCRIPTION_VAULT

    def is_amount_enough(self, amount):
        return amount - self.doc[COL_ORDERS_ELA_AMOUNT] > -self.doc[COL_ORDERS_ELA_AMOUNT] * 0.01

    def belongs(self, user_did):
        return user_did == self.doc[USR_DID]

    def is_settled(self):
        return self.doc[COL_ORDERS_CONTRACT_ORDER_ID] is not None

    def set_proof(self, proof):
        self.doc[COL_ORDERS_PROOF] = proof

    def get_proof_details(self):
        return {
            "interim_orderid": str(self.doc['_id']),
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "paying_did": self.doc[USR_DID],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "create_time": int(self.doc['created']),
            "expiration_time": int(self.doc[COL_ORDERS_EXPIRE_TIME]),
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS],
            "state": self.doc[COL_ORDERS_STATUS],
        }

    def get_receipt_proof_details(self, receipt: Receipt):
        return {
            "receipt_id": str(receipt.get_id()),
            "order_id": self.doc[COL_ORDERS_CONTRACT_ORDER_ID],
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "paid_did": self.doc[USR_DID],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "create_time": int(datetime.now().timestamp()),
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS]
        }

    def to_place_order(self):
        """ for the response of API """
        return {
            "interim_orderid": str(self.doc['_id']),
            "subscription": self.doc[COL_ORDERS_SUBSCRIPTION],
            "pricing_plan": self.doc[COL_ORDERS_PRICING_NAME],
            "paying_did": self.doc[USR_DID],
            "payment_amount": self.doc[COL_ORDERS_ELA_AMOUNT],
            "create_time": int(self.doc['created']),
            "expiration_time": int(self.doc[COL_ORDERS_EXPIRE_TIME]),
            "receiving_address": self.doc[COL_ORDERS_ELA_ADDRESS],
            "state": self.doc[COL_ORDERS_STATUS],
            "proof": self.doc[COL_ORDERS_PROOF]
        }

    def to_get_orders(self):
        """ for the response of API """
        doc = self.to_place_order()
        doc['order_id'] = self.doc[COL_ORDERS_CONTRACT_ORDER_ID]
        if not doc['order_id'] and doc['expiration_time'] < int(datetime.now().timestamp()):
            doc['state'] = COL_ORDERS_STATUS_EXPIRED
        return doc


class OrderManager:
    def __init__(self):
        self.ela_address = hive_setting.PAYMENT_RECEIVING_ADDRESS
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()
        self.backup_manager = BackupManager()

    def get_orders(self, user_did, subscription: t.Optional[str], contract_order_id: t.Optional[int]):
        """ get orders by conditional options: subscription, contract_order_id """
        col = self.mcli.get_management_collection(COL_ORDERS)

        filter_ = {USR_DID: user_did}
        if subscription is not None:
            filter_[COL_ORDERS_SUBSCRIPTION] = subscription
        if contract_order_id is not None:
            filter_[COL_ORDERS_CONTRACT_ORDER_ID] = contract_order_id

        docs = col.find_many(filter_)
        return [Order(doc) for doc in docs]

    def get_order(self, user_did, order_id):
        """ get by internal id """
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc = col.find_one({'_id': ObjectId(order_id), USR_DID: user_did})
        if not doc:
            raise OrderNotFoundException()
        return Order(doc)

    def get_order_by_proof(self, user_did, proof: str):
        """ get by internal id """
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc = col.find_one({COL_ORDERS_PROOF: proof, USR_DID: user_did})
        if not doc:
            raise OrderNotFoundException()
        return Order(doc)

    def get_receipts(self, user_did=None, contract_order_id: t.Optional[int] = None):
        """ get receipt by conditional options: contract_order_id

        Maybe for the provider service.
        """
        col = self.mcli.get_management_collection(COL_RECEIPTS)

        filter_ = {}
        if user_did is not None:
            filter_[USR_DID] = user_did
        if contract_order_id is not None:
            filter_[COL_ORDERS_CONTRACT_ORDER_ID] = contract_order_id

        docs = col.find_many(filter_)
        return [Receipt(doc) for doc in docs]

    def insert_order(self, user_did, subscription: str, plan: dict):
        exp = int(datetime.now().timestamp()) + 7 * 24 * 3600
        doc = {
            USR_DID: user_did,
            VERSION: PaymentConfig.get_all_package_info().get('version', '1.0'),
            COL_ORDERS_SUBSCRIPTION: subscription,
            COL_ORDERS_PRICING_NAME: plan['name'],
            COL_ORDERS_ELA_AMOUNT: plan['amount'],
            COL_ORDERS_ELA_ADDRESS: self.ela_address,
            COL_ORDERS_EXPIRE_TIME: exp,
            COL_ORDERS_CONTRACT_ORDER_ID: None,
            COL_ORDERS_PROOF: None,
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_NORMAL
        }
        col = self.mcli.get_management_collection(COL_ORDERS)
        doc['_id'] = ObjectId(col.insert_one(doc)['inserted_id'])
        return Order(doc)

    def update_proof(self, order: Order, proof: str):
        col = self.mcli.get_management_collection(COL_ORDERS)
        col.update_one({'_id': order.get_id()}, {'$set': {COL_ORDERS_PROOF: proof}})
        order.set_proof(proof)

    def update_contract_order_id(self, order: Order, contract_order_id: int):
        col = self.mcli.get_management_collection(COL_ORDERS)
        update = {
            COL_ORDERS_CONTRACT_ORDER_ID: contract_order_id,
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_PAID
        }
        col.update_one({'_id': order.get_id()}, {'$set': update})

    def insert_receipt(self, user_did, order: Order):
        receipt = {
            USR_DID: user_did,
            COL_ORDERS_SUBSCRIPTION: order.get_subscription(),
            COL_ORDERS_PRICING_NAME: order.get_plan()['name'],
            COL_ORDERS_ELA_AMOUNT: order.get_amount(),
            COL_ORDERS_ELA_ADDRESS: order.get_receiving_address(),
            COL_ORDERS_CONTRACT_ORDER_ID: order.get_contract_order_id(),
            COL_ORDERS_PROOF: None,
            COL_ORDERS_STATUS: COL_ORDERS_STATUS_NORMAL,
            COL_RECEIPTS_ORDER_ID: str(order.get_id()),
            COL_RECEIPTS_PAID_DID: user_did,
        }
        col = self.mcli.get_management_collection(COL_RECEIPTS)
        receipt['_id'] = ObjectId(col.insert_one(receipt)['inserted_id'])
        return Receipt(receipt)

    def update_receipt_proof(self, receipt: Receipt, receipt_proof: str):
        col = self.mcli.get_management_collection(COL_RECEIPTS)
        col.update_one({'_id': receipt.get_id()}, {'$set': {COL_ORDERS_PROOF: receipt_proof}})
        receipt.set_proof(receipt_proof)

    def upgrade_vault_or_backup(self, user_did, order: Order):
        plan = order.get_plan()
        if order.is_for_vault():
            self.vault_manager.upgrade(user_did, plan)
        else:
            self.backup_manager.upgrade(user_did, plan)

    def archive_orders_receipts(self, user_did):
        """ for unsubscribe the vault

        After unsubscribe the vault belonged to user, all orders and receipt need be marked to archive status.
        """
        col = self.mcli.get_management_collection(COL_ORDERS)
        col.update_one({USR_DID: user_did}, {'$set': {COL_ORDERS_STATUS: COL_ORDERS_STATUS_ARCHIVE}})

        col = self.mcli.get_management_collection(COL_RECEIPTS)
        col.update_one({USR_DID: user_did}, {'$set': {COL_ORDERS_STATUS: COL_ORDERS_STATUS_ARCHIVE}})
