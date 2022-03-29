import json
import operator
import sys
import unittest
import logging

from flask import appcontext_pushed, g
from contextlib import contextmanager

from pymongo import MongoClient

# from hive import create_app, hive_setting
from hive.settings import hive_setting
from hive.util.constants import DID_INFO_DB_NAME, HIVE_MODE_TEST, SUB_MESSAGE_COLLECTION, SUB_MESSAGE_PUB_DID, \
    SUB_MESSAGE_PUB_APPID, PUB_CHANNEL_COLLECTION, PUB_CHANNEL_PUB_DID, PUB_CHANNEL_PUB_APPID
from hive.util.error_code import ALREADY_EXIST, NOT_FOUND
from src import create_app
from tests_v1 import test_common
from tests_v1.hive_auth_test import DIDApp, DApp

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HivePubsubTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HivePubsubTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HivePubsubTestCase").debug("Setting up HivePubsubTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HivePubsubTestCase").debug("\n\nShutting down HivePubsubTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HivePubsubTestCase").info("\n")
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
        self.clean_pub_channel_db(self.did, self.app_id)
        self.clean_sub_message_db(self.did, self.app_id)

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

    def clean_pub_channel_db(self, pub_did, pub_appid):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URI)

        db = connection[DID_INFO_DB_NAME]
        col = db[PUB_CHANNEL_COLLECTION]
        query = {
            PUB_CHANNEL_PUB_DID: pub_did,
            PUB_CHANNEL_PUB_APPID: pub_appid
        }
        col.delete_many(query)

    def clean_sub_message_db(self, pub_did, pub_appid):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URI)

        db = connection[DID_INFO_DB_NAME]
        col = db[SUB_MESSAGE_COLLECTION]
        query = {
            SUB_MESSAGE_PUB_DID: pub_did,
            SUB_MESSAGE_PUB_APPID: pub_appid,
        }
        col.delete_many(query)

    def get_auth(self, token):
        auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]
        return auth

    def publish_channel(self, channel_name):
        data = {
            "channel_name": channel_name
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/publish',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def subscribe_channel(self, pub_did, pub_appid, channel_name, token):
        auth = self.get_auth(token)
        data = {
            "pub_did": pub_did,
            "pub_app_id": pub_appid,
            "channel_name": channel_name
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/subscribe',
                                  data=json.dumps(data),
                                  headers=auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def push_message(self, channel_name, message):
        data = {
            "channel_name": channel_name,
            "message": message
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/push',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def pop_message(self, pub_did, pub_appid, channel_name, limit, token):
        auth = self.get_auth(token)
        data = {
            "pub_did": pub_did,
            "pub_app_id": pub_appid,
            "channel_name": channel_name,
            "message_limit": limit
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/pop',
                                  data=json.dumps(data),
                                  headers=auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        return r["messages"]

    def test_publish_and_subscribe(self):
        logging.getLogger("HivePubsubTestCase").debug("\nRunning test_1_publish_and_subscribe")
        self.publish_channel("test_channel1")
        self.publish_channel("test_channel2")

        r, s = self.parse_response(
            self.test_client.get('/api/v1/pubsub/pub/channels', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        channels = ["test_channel1", "test_channel2"]
        self.assertTrue(operator.eq(r["channels"], channels))

        self.user_did1 = DIDApp("didapp1",
                                "clever bless future fuel obvious black subject cake art pyramid member clump")
        self.testapp1 = DApp("testapp", test_common.app_id,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        self.testapp2 = DApp("testapp", test_common.app_id,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        token1, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp1)
        token2, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp2)
        # token1 -> channel1 and channel2, token2 -> channel1
        self.subscribe_channel(self.did, self.app_id, "test_channel1", token1)
        self.subscribe_channel(self.did, self.app_id, "test_channel1", token2)
        self.subscribe_channel(self.did, self.app_id, "test_channel2", token1)

        # push msg 1-30 to channel1
        for i in range(0, 30):
            self.push_message("test_channel1", f"message_{str(i)}")
        # contains msg 1-10
        messages = list()
        for i in range(0, 10):
            messages.append(f"message_{str(i)}")
        # channel1 out 10 with token1
        messages1 = self.pop_message(self.did, self.app_id, "test_channel1", 10, token1)
        messages1_list = list()
        for m in messages1:
            messages1_list.append(m["message"])
        self.assertTrue(operator.eq(messages1_list, messages))
        # last 20 msgs.
        messages = list()
        for i in range(10, 30):
            messages.append(f"message_{str(i)}")

        messages2 = self.pop_message(self.did, self.app_id, "test_channel1", 20, token2)
        messages2_list = list()
        for m in messages2:
            messages2_list.append(m["message"])
        self.assertTrue(operator.eq(messages2_list, messages))

    def test_publish_duplicate_channel(self):
        logging.getLogger("HivePubsubTestCase").debug("\nRunning test_1_publish_and_subscribe")
        self.publish_channel("test_channel1")
        data = {
            "channel_name": "test_channel1"
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/publish',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assertEqual(s, ALREADY_EXIST)

    def test_remove_channel(self):
        self.publish_channel("test_channel1")
        data = {
            "channel_name": "test_channel1"
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/remove',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assert200(s)
        r, s = self.parse_response(
            self.test_client.get('/api/v1/pubsub/pub/channels', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertTrue(operator.eq(r["channels"], list()))

        # remove a not existing channel
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/remove',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assert200(s)

    def test_unsubscribe_channel(self):
        self.publish_channel("test_channel1")
        self.user_did1 = DIDApp("didapp1",
                                "clever bless future fuel obvious black subject cake art pyramid member clump")
        self.testapp1 = DApp("testapp", test_common.app_id,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        self.testapp2 = DApp("testapp", test_common.app_id2,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        token1, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp1)
        token2, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp2)
        self.subscribe_channel(self.did, self.app_id, "test_channel1", token1)
        self.subscribe_channel(self.did, self.app_id, "test_channel1", token2)

        data = {
            "pub_did": self.did,
            "pub_app_id": self.app_id,
            "channel_name": "test_channel1"
        }
        auth1 = self.get_auth(token1)
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/unsubscribe',
                                  data=json.dumps(data),
                                  headers=auth1)
        )
        self.assert200(s)
        r, s = self.parse_response(
            self.test_client.get('/api/v1/pubsub/sub/channels', headers=auth1)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertTrue(operator.eq(r["channels"], list()))

        # unsubscribe again, should be ok
        auth1 = self.get_auth(token1)
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/unsubscribe',
                                  data=json.dumps(data),
                                  headers=auth1)
        )
        self.assert200(s)

        # unsubscribe no existing channel, should be ok
        no_channle = {
            "pub_did": self.did,
            "pub_app_id": self.app_id,
            "channel_name": "no_channel"
        }
        auth1 = self.get_auth(token1)
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/unsubscribe',
                                  data=json.dumps(no_channle),
                                  headers=auth1)
        )
        self.assert200(s)

        auth2 = self.get_auth(token2)
        r, s = self.parse_response(
            self.test_client.get('/api/v1/pubsub/sub/channels', headers=auth2)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertTrue(operator.eq(r["channels"], ["test_channel1"]))

    def test_subscribe_empty_channel(self):
        channel_name = "test_channel1"
        self.user_did1 = DIDApp("didapp1",
                                "clever bless future fuel obvious black subject cake art pyramid member clump")
        self.testapp1 = DApp("testapp", test_common.app_id,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        token, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp1)
        auth = self.get_auth(token)
        data = {
            "pub_did": self.did,
            "pub_app_id": self.app_id,
            "channel_name": channel_name
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/subscribe',
                                  data=json.dumps(data),
                                  headers=auth)
        )
        self.assertEqual(NOT_FOUND, s)

    def test_push_an_empty_channel(self):
        data = {
            "channel_name": "no_channel",
            "message": "some message"
        }
        r, s = self.parse_response(
            self.test_client.post('/api/v1/pubsub/push',
                                  data=json.dumps(data),
                                  headers=self.auth)
        )
        self.assertEqual(NOT_FOUND, s)

    def test_pop_an_empty_channel(self):
        self.user_did1 = DIDApp("didapp",
                                "clever bless future fuel obvious black subject cake art pyramid member clump")
        self.testapp1 = DApp("testapp", test_common.app_id,
                             "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        token1, hive_did = test_common.test_auth_common(self, self.user_did1, self.testapp1)
        messages1 = self.pop_message(self.did, self.app_id, "test_channel1", 10, token1)
        self.assertTrue(operator.eq(messages1, list()))


if __name__ == '__main__':
    unittest.main()
