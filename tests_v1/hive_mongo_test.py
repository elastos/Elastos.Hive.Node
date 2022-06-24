import json
import unittest
import flask_unittest

from src.utils.executor import executor
from tests import test_log
from tests_v1 import test_common
from hive.util.constants import HIVE_MODE_TEST
from src import create_app
from tests_v1.test_common import initialize_access_tokens


class HiveMongoDbTestCase(flask_unittest.ClientTestCase):
    app = create_app(mode=HIVE_MODE_TEST)

    @classmethod
    def setUpClass(cls):
        test_log("HiveMongoDbTestCase: Setting up HiveMongoDbTestCase\n")

    @classmethod
    def tearDownClass(cls):
        # wait flask-executor to finish
        executor.shutdown()
        test_log("HiveMongoDbTestCase: \n\nShutting down HiveMongoDbTestCase")

    def setUp(self, client):
        test_log("HiveMongoDbTestCase: \n")
        self.app.config['TESTING'] = True
        self.content_type = ("Content-Type", "application/json")
        self.json_header = [self.content_type, ]

        initialize_access_tokens(self, client)
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()

        test_common.create_vault_if_not_exist(self, client)
        self.create_collection(client)

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self, client):
        test_common.delete_test_auth_token()
        test_log("HiveMongoDbTestCase: \n")

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            test_log(f"HiveMongoDbTestCase: \nret: {str(r.get_data())}")
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def create_collection(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_1_create_collection")
        r, s = self.parse_response(
            client.post('/api/v1/db/create_collection', data=json.dumps({"collection": "works"}), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        r, s = self.parse_response(
            client.post('/api/v1/db/create_collection', data=json.dumps({"collection": "works"}), headers=self.auth)
        )
        self.assert200(s)
        self.assertTrue(r["existing"])

    def test_2_insert_one(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_2_insert_one")
        r, s = self.parse_response(
            client.post('/api/v1/db/insert_one', data=json.dumps(
                              {
                                  "collection": "works",
                                  "document": {
                                      "author": "john doe1",
                                      "title": "Eve for Dummies2"
                                  },
                                  "options": {"bypass_document_validation": False}
                              }
                          ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_3_insert_many(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_3_insert_many")
        r, s = self.parse_response(
            client.post('/api/v1/db/insert_many', data=json.dumps(
                              {
                                  "collection": "works",
                                  "document": [
                                      {
                                          "author": "john doe1",
                                          "title": "Eve for Dummies1_2"
                                      },
                                      {
                                          "author": "john doe2",
                                          "title": "Eve for Dummies2"
                                      },
                                      {
                                          "author": "john doe3",
                                          "title": "Eve for Dummies3"
                                      }
                                  ],
                                  "options": {"bypass_document_validation": False, "ordered": True}
                              }
                          ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_4_count_documents(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_8_count_documents")
        r, s = self.parse_response(
            client.post('/api/v1/db/count_documents', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe1_1",
                                          },
                                          "options": {
                                              "skip": 0,
                                              "limit": 10,
                                              "maxTimeMS": 1000000000
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_find_one(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_9_find_one")
        r, s = self.parse_response(
            client.post('/api/v1/db/find_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe2",
                                          },
                                          "options": {
                                              "skip": 0,
                                              "projection": {"_id": False},
                                              "sort": {'_id': -1},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_6_1_find_one_null_filter(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_9_1_find_one_null_filter")
        r, s = self.parse_response(
            client.post('/api/v1/db/find_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "options": {
                                              "skip": 0,
                                              "projection": {"_id": False},
                                              "sort": {'_id': -1},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_7_find_many(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_10_find_many")
        r, s = self.parse_response(
            client.post('/api/v1/db/find_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe1"
                                          },
                                          "options": {
                                              "skip": 0,
                                              "limit": 3,
                                              "projection": {"_id": False},
                                              "sort": {"_id": -1},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_8_find_many_none_filter(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_10_find_many_none_filter")
        r, s = self.parse_response(
            client.post('/api/v1/db/find_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "options": {
                                              "skip": 0,
                                              "limit": 3,
                                              "projection": {"_id": False},
                                              "sort": {"_id": -1},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_9_update_one(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_4_update_one")
        r, s = self.parse_response(
            client.post('/api/v1/db/update_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1"
                                          },
                                          "update": {"$set": {
                                              "author": "john doe3_1",
                                              "title": "Eve for Dummies3_1"
                                          }},
                                          "options": {
                                              "upsert": True,
                                              "bypass_document_validation": False
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_10_update_many(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_5_update_many")
        r, s = self.parse_response(
            client.post('/api/v1/db/update_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe2",
                                          },
                                          "update": {"$set": {
                                              "author": "john doe1_1",
                                              "title": "Eve for Dummies1_1"
                                          }},
                                          "options": {
                                              "upsert": True,
                                              "bypass_document_validation": False
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_11_delete_one(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_6_delete_one")
        r, s = self.parse_response(
            client.post('/api/v1/db/delete_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_12_delete_many(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_7_delete_many")
        r, s = self.parse_response(
            client.post('/api/v1/db/delete_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_13_delete_collection(self, client):
        test_log("HiveMongoDbTestCase: \nRunning test_1_2_delete_collection")
        r, s = self.parse_response(
            client.post('/api/v1/db/delete_collection', data=json.dumps(
                                      {
                                          "collection": "works"
                                      }
                                  ), headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        r, s = self.parse_response(
            client.post('/api/v1/db/insert_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "document": {
                                              "author": "john doe1",
                                              "title": "Eve for Dummies2"
                                          },
                                          "options": {"bypass_document_validation": False}
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)

        r, s = self.parse_response(
            client.post('/api/v1/db/insert_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "document": [
                                              {
                                                  "author": "john doe1",
                                                  "title": "Eve for Dummies1_2"
                                              },
                                              {
                                                  "author": "john doe2",
                                                  "title": "Eve for Dummies2"
                                              },
                                              {
                                                  "author": "john doe3",
                                                  "title": "Eve for Dummies3"
                                              }
                                          ],
                                          "options": {"bypass_document_validation": False, "ordered": True}
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)

        r, s = self.parse_response(
            client.post('/api/v1/db/update_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1"
                                          },
                                          "update": {"$set": {
                                              "author": "john doe3_1",
                                              "title": "Eve for Dummies3_1"
                                          }},
                                          "options": {
                                              "upsert": True,
                                              "bypass_document_validation": False
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)

        r, s = self.parse_response(
            client.post('/api/v1/db/update_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe1",
                                          },
                                          "update": {"$set": {
                                              "author": "john doe1_1",
                                              "title": "Eve for Dummies1_1"
                                          }},
                                          "options": {
                                              "upsert": True,
                                              "bypass_document_validation": False
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)

        r, s = self.parse_response(
            client.post('/api/v1/db/delete_one', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)

        r, s = self.parse_response(
            client.post('/api/v1/db/delete_many', data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ), headers=self.auth)
        )
        self.assertEqual(s, 404)


if __name__ == '__main__':
    unittest.main()
