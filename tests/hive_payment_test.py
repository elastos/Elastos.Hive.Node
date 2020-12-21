import sys
import unittest

from flask import appcontext_pushed, g
from contextlib import contextmanager

from hive import create_app
from tests import test_common
from hive.util.payment.vault_order import *
from hive.util.payment.vault_service_manage import *

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
        self.init_payment_db()

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

    def init_payment_db(self):
        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
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
                     VAULT_ORDER_TXIDS: ["4813ba481d0e18c4fa03ddc35c32ffbd88080fba14fec8c0c31e5843e6399940"],
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
        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
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
        tx = "4813ba481d0e18c4fa03ddc35c32ffbd88080fba14fec8c0c31e5843e6399940"
        address = "ETJqK7o7gBhzypmNJ1MstAHU2q77fo78jg"
        value, time = get_tx_info(tx, address)
        self.assertNotEqual(value, None)

    def test_1_get_vault_package_info(self):
        logging.getLogger("").debug("\nRunning test_1_get_vault_package_info")
        r, s = self.parse_response(
            self.test_client.get('api/v1/payment/vault_package_info', headers=self.auth)
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

    def test_2_0_create_vault(self):
        logging.getLogger("").debug("\nRunning test_2_0_create_vault")

        r, s = self.parse_response(
            self.test_client.post('/api/v1/service/vault/create',
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertTrue(r)

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
        pay_param = {
            "order_id": self.test_order_id,
            "pay_txids": ["4813ba481d0e18c4fa03ddc35c32ffbd88080fba14fec8c0c31e5843e6399940"]
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
        self.assertTrue(r)

    def test_5_service_storage(self):
        test_common.setup_test_vault(self.did)
        count_vault_storage_job()
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertTrue(r)
        inc_vault_file_use_storage_byte(self.did, 55000000)
        update_vault_db_use_storage_byte(self.did, 55000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertFalse(r)
        inc_vault_file_use_storage_byte(self.did, -20000000)
        update_vault_db_use_storage_byte(self.did, 30000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertTrue(r)

    def assert_service_vault_info(self, state):
        r, s = self.parse_response(
            self.test_client.get('api/v1/service/vault', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertEqual(r["vault_service_info"][VAULT_SERVICE_PRICING_USING], state)

    def test_6_service_management_timeout_ONLY_READ(self):
        test_common.setup_test_vault(self.did)
        now = datetime.utcnow().timestamp()
        self.change_service(now - 24 * 60 * 60, now - 1, 5000, "Rookie")
        count_vault_storage_job()
        self.assert_service_vault_info("Rookie")
        inc_vault_file_use_storage_byte(self.did, 910000000)
        update_vault_db_use_storage_byte(self.did, 910000000)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertTrue(r)
        proc_expire_vault_job()
        self.assert_service_vault_info("Free")
        r, msg = can_access_vault(self.did, VAULT_ACCESS_R)
        self.assertTrue(r)
        r, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertFalse(r)


if __name__ == '__main__':
    unittest.main()
