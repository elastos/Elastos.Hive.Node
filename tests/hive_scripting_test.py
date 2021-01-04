import json
import sys
import time
import unittest
import logging
from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive import create_app, HIVE_MODE_TEST
from tests import test_common
from tests.test_common import did

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveMongoScriptingTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveMongoScriptingTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveMongoScriptingTestCase").debug("Setting up HiveMongoScriptingTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\n\nShutting down HiveMongoScriptingTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveMongoScriptingTestCase").info("\n")
        self.app = create_app(mode=HIVE_MODE_TEST)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()
        test_common.setup_test_vault(self.did)
        self.init_collection_for_test()

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self):
        test_common.delete_test_auth_token()
        logging.getLogger("HiveMongoScriptingTestCase").info("\n")

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            logging.getLogger("HiveMongoScriptingTestCase").debug("\nret:" + str(r.get_data()))
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def init_collection_for_test(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning init_collection_for_test")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/create_collection',
                                  data=json.dumps(
                                      {
                                          "collection": "groups"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/insert_one',
                                  data=json.dumps(
                                      {
                                          "collection": "groups",
                                          "document": {
                                              "friends": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_set_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_1_set_script_without_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "groups",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_2_set_script_with_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_2_set_script_with_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          },
                                          "condition": {
                                              "type": "queryHasResults",
                                              "name": "verify_user_permission",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "_id": "$params.group_id",
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_3_set_script_with_complex_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_3_set_script_with_complex_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_complex_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          },
                                          "condition": {
                                              "type": "and",
                                              "name": "verify_user_permission",
                                              "body": [
                                                  {
                                                      "type": "queryHasResults",
                                                      "name": "user_in_group",
                                                      "body": {
                                                          "collection": "test_group",
                                                          "filter": {
                                                              "_id": "$params.group_id",
                                                              "friends": "$caller_did"
                                                          }
                                                      }
                                                  },
                                                  {
                                                      "type": "queryHasResults",
                                                      "name": "user_in_group",
                                                      "body": {
                                                          "collection": "test_group",
                                                          "filter": {
                                                              "_id": "$params.group_id",
                                                              "friends": "$caller_did"
                                                          }
                                                      }
                                                  }
                                              ]
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_4_set_script_with_anonymous_access(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_1_set_script_with_anonymous_access")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_anonymous_access",
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "type": "find",
                                              "name": "get_all_groups",
                                              "body": {
                                                  "collection": "groups"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_7_run_script_with_anonymous_access(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_run_script_with_anonymous_access")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_anonymous_access",
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_run_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_run_script_without_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_1_run_other_user_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_1_run_other_user_script_without_condition")

        token = test_common.get_auth_token2()
        auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition",
                                          "context": {
                                              "target_did": test_common.did,
                                              "target_app_did": test_common.app_id
                                          }
                                      }
                                  ),
                                  headers=auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_6_run_script_with_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_5_run_script_with_condition")

        # Set up the pre-requisites to run this test
        self.test_client.post('/api/v1/db/create_collection',
                              data=json.dumps({"collection": "test_group"}),
                              headers=self.auth)
        r, s = self.parse_response(self.test_client.post('/api/v1/db/insert_one',
                                                         data=json.dumps({"collection": "test_group",
                                                                          "document": {"name": "Trinity",
                                                                                       "friends": [did]}}),
                                                         headers=self.auth))
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        # Run the actual test
        group_id = r["inserted_id"]
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_condition",
                                          "params": {
                                              "group_id": {"$oid": group_id}
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        # Tear down
        self.test_client.post('/api/v1/db/delete_collection',
                              data=json.dumps({"collection": "test_group"}),
                              headers=self.auth)


if __name__ == '__main__':
    unittest.main()
