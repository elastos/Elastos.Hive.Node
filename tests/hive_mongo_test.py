import json
import sys
import time
import unittest
import logging
from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive import create_app
from tests import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveMongoDbTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveMongoDbTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveMongoDbTestCase").debug("Setting up HiveMongoDbTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveMongoDbTestCase").debug("\n\nShutting down HiveMongoDbTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveMongoDbTestCase").info("\n")
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        test_common.setup_sync_record()
        self.init_auth()

    def init_auth(self):
        token = test_common.get_auth_token(self)
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self):
        test_common.delete_test_auth_token()
        test_common.delete_sync_record()
        logging.getLogger("HiveMongoDbTestCase").info("\n")

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            logging.getLogger("HiveMongoDbTestCase").debug("\nret:" + str(r.get_data()))
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def test_1_create_collection(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_1_create_collection")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/create_collection',
                                  data=json.dumps(
                                      {
                                          "collection": "works"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_2_delete_collection(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_1_2_delete_collection")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/delete_collection',
                                  data=json.dumps(
                                      {
                                          "collection": "works"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_2_insert_one(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_2_insert_one")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/insert_one',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "document": {
                                              "author": "john doe1",
                                              "title": "Eve for Dummies2"
                                          },
                                          "options": {"bypass_document_validation": False}
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_3_insert_many(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_3_insert_many")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/insert_many',
                                  data=json.dumps(
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
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_4_update_one(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_4_update_one")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/update_one',
                                  data=json.dumps(
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
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_update_many(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_5_update_many")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/update_many',
                                  data=json.dumps(
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
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_6_delete_one(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_6_delete_one")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/delete_one',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_7_delete_many(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_7_delete_many")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/delete_many',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe3_1",
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_8_count_documents(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_8_count_documents")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/count_documents',
                                  data=json.dumps(
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
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_9_find_one(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_9_find_one")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/find_one',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                              "author": "john doe2",
                                          },
                                          "options": {
                                              "skip": 0,
                                              "projection": {"_id": False},
                                              "sort": {'_id': 'desc'},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_9_1_find_one_null_filter(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_9_1_find_one_null_filter")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/find_one',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "options": {
                                              "skip": 0,
                                              "projection": {"_id": False},
                                              "sort": {'_id': 'desc'},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_10_find_many(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_10_find_many")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/find_many',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "filter": {
                                            "author": "john doe1"
                                          },
                                          "options": {
                                              "skip": 0,
                                              "limit": 3,
                                              "projection": {"_id": False},
                                              "sort": {"_id": "desc"},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_10_find_many_none_filter(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_10_find_many_none_filter")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/find_many',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "options": {
                                              "skip": 0,
                                              "limit": 3,
                                              "projection": {"_id": False},
                                              "sort": {"_id": "desc"},
                                              "allow_partial_results": False,
                                              "return_key": False,
                                              "show_record_id": False,
                                              "batch_size": 0
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")


if __name__ == '__main__':
    unittest.main()
