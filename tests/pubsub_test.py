# -*- coding: utf-8 -*-

"""
Testing file for the pubsub module.
"""
import json
import unittest
import websocket

from tests.utils.http_client import HttpClient
from tests import init_test, RA


class PubSubTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2', is_owner=True)

        self.message_name = 'pubsub_test_message'
        self.collection_name = 'pubsub_test_col'

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_register(self):
        response = self.cli.put(f'/vault/pubsub/{self.message_name}', {
            'type': 'countDocs',
            'body': {
                'collections': [{
                    'name': 'pubsub_test_col',
                    'field': 'created',
                    'inside': 3600
                }],
                'interval': 5
            }
        })
        self.assertIn(response.status_code, [200])

    def test02_hello(self):
        ws = websocket.WebSocket()
        ws.connect("ws://127.0.0.1:5005/ws/echo")
        msg = "Hello, Server"
        ws.send(msg)
        data = ws.recv()
        self.assertEqual(data, msg)

    def test02_message(self):
        websocket.enableTrace(True)

        # prepare data
        response = self.cli.delete(f'/vault/db/{self.collection_name}')
        RA(response).assert_status(204)
        response = self.cli.put(f'/vault/db/collections/{self.collection_name}')
        RA(response).assert_status(200, 455)

        response = self.cli.post(f'/vault/db/collection/{self.collection_name}', body={
            'document': [{'name': 'zhangsan'}]
        })
        RA(response).assert_status(201)

        # check message
        ws = websocket.WebSocket()
        ws.connect("ws://127.0.0.1:5005/ws/pubsub/message", header={})
        data = {
            "token": self.cli.get_token()
        }
        ws.send(json.dumps(data))
        data_str = ws.recv()
        data = json.loads(data_str)
        self.assertEqual(data['collections'][0][self.collection_name], 1)

        # clean data
        response = self.cli.delete(f'/vault/db/{self.collection_name}')
        RA(response).assert_status(204)

    def test03_unregister(self):
        response = self.cli.delete(f'/vault/pubsub/{self.message_name}')
        self.assertIn(response.status_code, [204])
