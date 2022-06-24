import unittest

from src import create_app
from hive.util.payment.vault_order import *
from hive.util.payment.vault_service_manage import *
from src.utils.executor import executor
from tests import test_log
from tests_v1 import test_common


class SubscriptionTestCase(unittest.TestCase):
    app = create_app(mode=HIVE_MODE_TEST)

    def __init__(self, methodName='runTest'):
        super(SubscriptionTestCase, self).__init__(methodName)

    def setUp(self):
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()

        test_common.setup_test_auth_token()
        self.auth = [
            ("Authorization", "token " + test_common.get_auth_token()),
            ("Content-Type", "application/json"),
        ]
        self.did = test_common.get_auth_did()

    @classmethod
    def tearDownClass(cls):
        # wait flask-executor to finish
        executor.shutdown()

    def test01_create_vault(self):
        test_log("\nRunning test01_create_vault")

        response = self.test_client.post('/api/v1/service/vault/create', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.get_data())
        self.assertEqual(body["_status"], "OK")
        result, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(result, SUCCESS)

    def test02_get_vault_info(self):
        test_log("\nRunning test02_get_vault_info")

        response = self.test_client.get('/api/v1/service/vault', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.get_data())
        self.assertEqual(body["_status"], "OK")
        self.assertEqual(body["vault_service_info"][VAULT_SERVICE_PRICING_USING], 'Free')

    def test03_remove_vault(self):
        test_log("\nRunning test_2_0_remove_vault")

        response = self.test_client.post('/api/v1/service/vault/remove', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.get_data())
        self.assertEqual(body["_status"], "OK")
        result, msg = can_access_vault(self.did, VAULT_ACCESS_WR)
        self.assertEqual(result, NOT_FOUND)


if __name__ == '__main__':
    unittest.main()
