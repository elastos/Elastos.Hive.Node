# -*- coding: utf-8 -*-

"""
Testing file for the database module.
"""

import unittest

import pymongo

from tests.utils.http_client import HttpClient
from tests import init_test


class DatabaseTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.collection_name = 'test_collection'
        self.name_not_exist = 'name_not_exist_collection'

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_create_collection(self):
        response = self.cli.put(f'/db/collections/{self.collection_name}')
        self.assertTrue(response.status_code in [200, 455])
        if response.status_code == 200:
            self.assertEqual(response.json().get('name'), self.collection_name)

    def test02_insert_document(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            "document": [{
                    "author": "john doe1",
                    "title": "Eve for Dummies1",
                    "words_count": 10000
                }, {
                    "author": "john doe1",
                    "title": "Eve for Dummies1",
                    "words_count": 1000
                }, {
                    "author": "john doe2",
                    "title": "Eve for Dummies2",
                    "words_count": 10000
                }, {
                    "author": "john doe2",
                    "title": "Eve for Dummies2",
                    "words_count": 1000
                }
            ],
            "options": {
                "bypass_document_validation": False,
                "ordered": True
            }})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json().get('inserted_ids')), 4)

    def test02_insert_document_timestamp(self):
        # insert a new document with timestamp=True
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            "document": [{
                    "author": "timestamp_default",
                    "title": "Eve for Dummies1",
                    "words_count": 10000
                }
            ],
            "options": {
                "bypass_document_validation": False,
                "ordered": True
            }})
        self.assertEqual(response.status_code, 201)
        # check if the inserted document contains two new fields: created, modified.
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"timestamp_default"}&skip=0')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('items' in response.json())
        self.assertTrue('created' in response.json()['items'][0])
        self.assertTrue('modified' in response.json()['items'][0])

        # insert a new document with timestamp=False
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            "document": [{
                    "author": "timestamp_false",
                    "title": "Eve for Dummies1",
                    "words_count": 10000
                }
            ],
            "options": {
                "bypass_document_validation": False,
                "ordered": True,
                "timestamp": False
            }})
        self.assertEqual(response.status_code, 201)
        # check if the inserted document contains two new fields: created, modified.
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"timestamp_false"}&skip=0')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('items' in response.json())
        self.assertTrue('created' not in response.json()['items'][0])
        self.assertTrue('modified' not in response.json()['items'][0])

    def test02_insert_document_invalid_parameter(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}')
        self.assertEqual(response.status_code, 400)

    def test03_update_document(self):
        response = self.cli.patch(f'/db/collection/{self.collection_name}', body={
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
            }})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('matched_count'), 2)

    def test03_update_document_invalid_parameter(self):
        response = self.cli.patch(f'/db/collection/{self.collection_name}')
        self.assertEqual(response.status_code, 400)

    def test03_update_one_document(self):
        response = self.cli.patch(f'/db/collection/{self.collection_name}?updateone=true', body={
            "filter": {
                "author": "john doe1_1",
            },
            "update": {"$set": {
                "author": "john doe1_2",
                "title": "Eve for Dummies1_2"
            }},
            "options": {
                "upsert": True,
                "bypass_document_validation": False
            }})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('matched_count'), 1)

    def test03_update_insert_if_not_exists(self):
        """
        Only use $setOnInsert to insert the document if not exists. The inserted document:
            {
                "_id": ObjectId("6241471ab042663cc9f179e7"),
                "author": "john doe4",
                "title": "Eve for Dummies4"
            }

        first result: '{"acknowledged": true, "matched_count": 0, "modified_count": 0, "upserted_id": "624148bab042663cc9f17c02"}'
        second result: '{"acknowledged": true, "matched_count": 1, "modified_count": 0, "upserted_id": null}'
        """
        response = self.cli.patch(f'/db/collection/{self.collection_name}', body={
            "filter": {
                "author": "john doe4",
            },
            "update": {"$setOnInsert": {
                "title": "Eve for Dummies4"
            }},
            "options": {
                "upsert": True,
                "bypass_document_validation": True,
                "timestamp": True
            }})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('matched_count') in [0, 1])

        # check if the inserted document contains two new fields: created, modified.
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"john doe4"}&skip=0')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('items' in response.json())
        self.assertTrue('created' in response.json()['items'][0])
        self.assertTrue('modified' in response.json()['items'][0])

    def test04_count_document(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}?op=count', body={
            "filter": {
                "author": "john doe2",
            },
            "options": {
                "skip": 0,
                "limit": 10,
                "maxTimeMS": 1000000000
            }})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json().get('count'), 2)

    def test04_count_document_invalid_parameter(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}?op=count')
        self.assertEqual(response.status_code, 400)

    def test05_find_document(self):
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"john doe2"}&skip=0')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('items' in response.json())

    def test05_find_document_invalid_parameter(self):
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter=&skip=')
        self.assertEqual(response.status_code, 400)

    def test06_query_document(self):
        response = self.cli.post(f'/db/query', body={
            "collection": self.collection_name,
            "filter": {
                "author": "john doe2",
                "words_count": {"$gt": 0, "$lt": 500000}
            },
            "options": {
                "skip": 0,
                "limit": 3,
                "projection": {
                    "modified": False
                },
                'sort': [('_id', pymongo.ASCENDING)],  # sort with mongodb style.
                "allow_partial_results": False,
                "return_key": False,
                "show_record_id": False,
                "batch_size": 0
            }})
        self.assertEqual(response.status_code, 201)
        self.assertTrue('items' in response.json())
        ids = list(map(lambda i: str(i['_id']), response.json()['items']))
        self.assertTrue(all(ids[i] <= ids[i+1] for i in range(len(ids) - 1)))

        response = self.cli.post(f'/db/query', body={
            "collection": self.collection_name,
            "filter": {
                "author": "john doe2",
                "words_count": {"$gt": 0, "$lt": 500000}
            },
            "options": {
                "skip": 0,
                "limit": 3,
                "projection": {
                    "modified": False
                },
                'sort': {'_id': pymongo.DESCENDING},  # sort with hive node style.
                "allow_partial_results": False,
                "return_key": False,
                "show_record_id": False,
                "batch_size": 0
            }})
        self.assertEqual(response.status_code, 201)
        self.assertTrue('items' in response.json())
        ids = list(map(lambda i: str(i['_id']), response.json()['items']))
        self.assertTrue(all(ids[i] >= ids[i + 1] for i in range(len(ids) - 1)))

    def test06_query_document_invalid_parameter(self):
        response = self.cli.post(f'/db/query')
        self.assertEqual(response.status_code, 400)

    def test07_delete_one_document(self):
        response = self.cli.delete(f'/db/collection/{self.collection_name}?deleteone=true', body={
            "filter": {
                "author": "john doe1_2",
            }}, is_json=True)
        self.assertEqual(response.status_code, 204)

    def test07_delete_one_document_invalid_parameter(self):
        response = self.cli.delete(f'/db/collection/{self.collection_name}?deleteone=true')
        self.assertEqual(response.status_code, 400)

    def test07_delete_document(self):
        response = self.cli.delete(f'/db/collection/{self.collection_name}', body={
            "filter": {
                "author": "john doe2",
            }}, is_json=True)
        self.assertEqual(response.status_code, 204)

    def test08_delete_collection_not_found(self):
        response = self.cli.delete(f'/db/{self.name_not_exist}')
        self.assertEqual(response.status_code, 404)

    def test08_delete_collection(self):
        response = self.cli.delete(f'/db/{self.collection_name}')
        self.assertTrue(response.status_code in [204, 404])


if __name__ == '__main__':
    unittest.main()
