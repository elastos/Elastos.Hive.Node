import json
import sys
import unittest

from flask import appcontext_pushed, g
from contextlib import contextmanager

from src import create_app
from tests_v1 import test_common
from hive.util.payment.vault_order import *
from hive.util.payment.vault_service_manage import *
from hive.settings import hive_setting

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HivePaymentTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HivePaymentTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HivePaymentTestCase").debug("Setting up HivePaymentTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HivePaymentTestCase").debug("\n\nShutting down HivePaymentTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HivePaymentTestCase").info("\n")
        self.app = create_app(mode=HIVE_MODE_TEST)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")
        self.upload_file_content_type = ("Content-Type", "multipart/form-data")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()
        self.test_order_id = None

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]
        self.upload_auth = [
            ("Authorization", "token " + token),
            # self.upload_file_content_type,
        ]

    def init_vault_payment_db(self):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URL)

        db = connection[DID_INFO_DB_NAME]
        order_col = db[VAULT_ORDER_COL]
        query = {VAULT_ORDER_DID: self.did}
        order_col.delete_many(query)
        service_col = db[VAULT_SERVICE_COL]
        service_col.delete_many(query)

        package_info = PaymentConfig.get_pricing_plan("Rookie")
        self.assertNotEqual(package_info, None)
        # init some cancel order to test cancel order txid use in new order
        order_dic = {VAULT_ORDER_DID: self.did,
                     VAULT_ORDER_APP_ID: self.app_id,
                     VAULT_ORDER_PACKAGE_INFO: package_info,
                     VAULT_ORDER_TXIDS: ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"],
                     VAULT_ORDER_TYPE: VAULT_ORDER_TYPE_VAULT,
                     VAULT_ORDER_STATE: VAULT_ORDER_STATE_CANCELED,
                     VAULT_ORDER_CREATE_TIME: 1591000001,
                     VAULT_ORDER_PAY_TIME: 1591000031,
                     VAULT_ORDER_MODIFY_TIME: 1591000031
                     }
        order_col.insert_one(order_dic)

        order_dic = {VAULT_ORDER_DID: self.did,
                     VAULT_ORDER_APP_ID: self.app_id,
                     VAULT_ORDER_PACKAGE_INFO: package_info,
                     VAULT_ORDER_TXIDS: [],
                     VAULT_ORDER_TYPE: VAULT_ORDER_TYPE_VAULT,
                     VAULT_ORDER_STATE: VAULT_ORDER_STATE_WAIT_PAY,
                     VAULT_ORDER_CREATE_TIME: (1591703671 + 36288000),
                     VAULT_ORDER_PAY_TIME: (1591703671 + 36288000),
                     VAULT_ORDER_MODIFY_TIME: (1591703671 + 36288000)
                     }
        ret = order_col.insert_one(order_dic)
        self.test_order_id = str(ret.inserted_id)

    def init_vault_backup_payment_db(self):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URL)

        db = connection[DID_INFO_DB_NAME]
        order_col = db[VAULT_ORDER_COL]
        query = {VAULT_ORDER_DID: self.did}
        order_col.delete_many(query)
        service_col = db[VAULT_SERVICE_COL]
        service_col.delete_many(query)

        package_info = PaymentConfig.get_backup_plan("Rookie")
        self.assertNotEqual(package_info, None)
        # init some cancel order to test cancel order txid use in new order
        order_dic = {VAULT_ORDER_DID: self.did,
                     VAULT_ORDER_APP_ID: self.app_id,
                     VAULT_ORDER_PACKAGE_INFO: package_info,
                     VAULT_ORDER_TXIDS: ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"],
                     VAULT_ORDER_STATE: VAULT_ORDER_STATE_CANCELED,
                     VAULT_ORDER_TYPE: VAULT_ORDER_TYPE_BACKUP,
                     VAULT_ORDER_CREATE_TIME: 1591000001,
                     VAULT_ORDER_PAY_TIME: 1591000031,
                     VAULT_ORDER_MODIFY_TIME: 1591000031
                     }
        order_col.insert_one(order_dic)

        order_dic = {VAULT_ORDER_DID: self.did,
                     VAULT_ORDER_APP_ID: self.app_id,
                     VAULT_ORDER_PACKAGE_INFO: package_info,
                     VAULT_ORDER_TXIDS: [],
                     VAULT_ORDER_TYPE: VAULT_ORDER_TYPE_BACKUP,
                     VAULT_ORDER_STATE: VAULT_ORDER_STATE_WAIT_PAY,
                     VAULT_ORDER_CREATE_TIME: (1591703671 + 36288000),
                     VAULT_ORDER_PAY_TIME: (1591703671 + 36288000),
                     VAULT_ORDER_MODIFY_TIME: (1591703671 + 36288000)
                     }
        ret = order_col.insert_one(order_dic)
        self.test_order_id = str(ret.inserted_id)

    def change_service(self, start_time, end_time, max_storage, pricing_name):
        info = get_vault_service(self.did)
        if not info:
            ret = setup_vault_service(self.did, max_storage, 1, pricing_name=pricing_name)
            _id = ret.upserted_id
        else:
            _id = info["_id"]

        _dic = {VAULT_SERVICE_START_TIME: start_time,
                VAULT_SERVICE_END_TIME: end_time,
                VAULT_SERVICE_MAX_STORAGE: max_storage,
                VAULT_SERVICE_PRICING_USING: pricing_name
                }
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URL)

        db = connection[DID_INFO_DB_NAME]
        col = db[VAULT_SERVICE_COL]
        query = {"_id": _id}
        value = {"$set": _dic}
        col.update_one(query, value)

    def tearDown(self):
        logging.getLogger("HivePaymentTestCase").info("\n")
        test_common.delete_test_auth_token()

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def test_0_get_tx(self):
        tx = "085ec55b07fe1c779eddfe256e6a5304b3663adf0c4bfa825a67b0ae400c1509"
        address = "EN9YK69ScA6WFgVQW3UZcmSRLSCStaU2pQ"
        value, time = get_tx_info(tx, address)
        self.assertNotEqual(value, None)

    def test_1_get_vault_package_info(self):
        logging.getLogger("").debug("\nRunning test_1_get_vault_package_info")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_info', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_1_get_vault_backup_pricing_plan(self):
        logging.getLogger("").debug("\nRunning test_1_1_get_vault_backup_package_info")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_backup_plan?name=Rookie', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_1_get_vault_pricing_plan(self):
        logging.getLogger("").debug("\nRunning test_1_1_get_vault_pricing_plan")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_pricing_plan?name=Rookie', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_2_get_payment_version(self):
        logging.getLogger("").debug("\nRunning test_1_2_get_payment_version")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/version', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_2_create_package_order(self):
        logging.getLogger("").debug("\nRunning test_2_create_package_order")

        package = {
            "pricing_name": "Rookie"
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/create_vault_package_order',
                                  data=json.dumps(package),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        order_id = r["order_id"]

        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_order?order_id=' + order_id, headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print(r)

    def test_3_get_all_order(self):
        logging.getLogger("").debug("\nRunning  test_3_get_all_order")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_order_list', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print(r)

    def test_4_pay_and_start_package_order(self):
        logging.getLogger("").debug("\nRunning test_4_pay_and_start_package_order")
        self.init_vault_payment_db()
        pay_param = {
            "order_id": self.test_order_id,
            "pay_txids": ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"]
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/pay_vault_package_order',
                                  data=json.dumps(pay_param),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        check_wait_order_tx_job()
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(r, SUCCESS)

    def test_5_service_storage(self):
        test_common.setup_test_vault(self.did)
        count_vault_storage_job()
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(r, SUCCESS)
        inc_vault_file_use_storage_byte(self.did, 55000000)
        update_vault_db_use_storage_byte(self.did, 55000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertNotEqual(r, SUCCESS)
        inc_vault_file_use_storage_byte(self.did, -20000000)
        update_vault_db_use_storage_byte(self.did, 30000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(r, SUCCESS)

    def assert_service_vault_info(self, state):
        r, s = self.parse_response(
            self.test_client.get('api/v1/service/vault', headers=self.auth)
        )
        if state:
            self.assert200(s)
            self.assertEqual(r["_status"], "OK")
            self.assertEqual(r["vault_service_info"][VAULT_SERVICE_PRICING_USING], state)
        else:
            self.assertEqual(404, s)

    def test_6_service_management_timeout_ONLY_READ(self):
        test_common.remove_test_vault(self.did)
        self.assert_service_vault_info(None)
        test_common.setup_test_vault(self.did)
        now = datetime.utcnow().timestamp()
        self.change_service(now - 24 * 60 * 60, now - 1, 5000, "Rookie")
        count_vault_storage_job()
        self.assert_service_vault_info("Rookie")
        inc_vault_file_use_storage_byte(self.did, 910000000)
        update_vault_db_use_storage_byte(self.did, 910000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(r, SUCCESS)
        proc_expire_vault_job()
        self.assert_service_vault_info("Free")
        r, msg = can_access_vault(self.did, VAULT_ACCESS_R)
        self.assertEqual(r, SUCCESS)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertNotEqual(r, SUCCESS)

    def test_7_create_package_order(self):
        logging.getLogger("").debug("\nRunning test_2_create_package_order")

        package = {
            "backup_name": "Rookie"
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/create_vault_package_order',
                                  data=json.dumps(package),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        order_id = r["order_id"]

        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_order?order_id=' + order_id, headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print(r)
        r, s = self.parse_response(
            self.test_client.post('/api/v1/service/vault/create',
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertTrue(r["existing"])

    def test_8_pay_and_start_backup_order(self):
        logging.getLogger("").debug("\nRunning test_4_pay_and_start_package_order")
        self.init_vault_backup_payment_db()
        pay_param = {
            "order_id": self.test_order_id,
            "pay_txids": ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"]
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/pay_vault_package_order',
                                  data=json.dumps(pay_param),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        check_wait_order_tx_job()
        self.assert_service_vault_backup_info("Rookie")

        r, s = self.parse_response(
            self.test_client.post('/api/v1/service/vault_backup/create',
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertTrue(r["existing"])

    def assert_service_vault_backup_info(self, state):
        r, s = self.parse_response(
            self.test_client.get('api/v1/service/vault_backup', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertEqual(r["vault_service_info"][VAULT_BACKUP_SERVICE_USING], state)

    def test_7_create_package_order(self):
        logging.getLogger("").debug("\nRunning test_2_create_package_order")

        package = {
            "backup_name": "Rookie"
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/create_vault_package_order',
                                  data=json.dumps(package),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        order_id = r["order_id"]

        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_order?order_id=' + order_id, headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print(r)

    def test_8_pay_and_start_backup_order(self):
        logging.getLogger("").debug("\nRunning test_4_pay_and_start_package_order")
        self.init_vault_backup_payment_db()
        pay_param = {
            "order_id": self.test_order_id,
            "pay_txids": ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"]
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/pay_vault_package_order',
                                  data=json.dumps(pay_param),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        check_wait_order_tx_job()
        self.assert_service_vault_backup_info("Rookie")

    def assert_service_vault_backup_info(self, state):
        r, s = self.parse_response(
            self.test_client.get('api/v1/service/vault/backup', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertEqual(r["vault_service_info"][VAULT_BACKUP_SERVICE_USING], state)

    def test_7_create_package_order(self):
        logging.getLogger("").debug("\nRunning test_2_create_package_order")

        package = {
            "backup_name": "Rookie"
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/create_vault_package_order',
                                  data=json.dumps(package),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        order_id = r["order_id"]

        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_order?order_id=' + order_id, headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print(r)

    def test_8_pay_and_start_backup_order(self):
        logging.getLogger("").debug("\nRunning test_4_pay_and_start_package_order")
        self.init_vault_backup_payment_db()
        pay_param = {
            "order_id": self.test_order_id,
            "pay_txids": ["5554d0af281ccce78bb9c2b8b77baad630a51bc67420a601566f8fa4106cfa92"]
        }

        r, s = self.parse_response(
            self.test_client.post('/api/v1/payment/pay_vault_package_order',
                                  data=json.dumps(pay_param),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        check_wait_order_tx_job()
        self.assert_service_vault_backup_info("Rookie")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/service/vault_backup/create',
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertTrue(r["existing"])

    def assert_service_vault_backup_info(self, state):
        r, s = self.parse_response(
            self.test_client.get('api/v1/service/vault_backup', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertEqual(r["vault_service_info"][VAULT_BACKUP_SERVICE_USING], state)


if __name__ == '__main__':
    unittest.main()
