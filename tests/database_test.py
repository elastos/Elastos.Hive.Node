# -*- coding: utf-8 -*-

"""
Testing file for the database module.
"""

import unittest

import pymongo

from tests.utils.http_client import HttpClient
from tests import init_test, VaultFreezer
from tests.utils.resp_asserter import RA, DictAsserter
from tests.utils.tester_http import HttpCode


class DatabaseTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.collection_name = 'test_collection'
        self.name_not_exist = 'name_not_exist_collection'

    @classmethod
    def setUpClass(cls):
        # subscribe vault
        HttpClient(f'/api/v2').put('/subscription/vault')

    def test01_create_collection(self):
        with VaultFreezer() as _:
            response = self.cli.put(f'/db/collections/{self.collection_name}')
            RA(response).assert_status(HttpCode.FORBIDDEN)

        response = self.cli.put(f'/db/collections/{self.collection_name}')
        RA(response).assert_status(200, 455)
        if response.status_code == 200:
            RA(response).body().assert_equal('name', self.collection_name)

    def __create_doc(self, index):
        return {'author': 'Alice',
                'title': f'The Metrix {index}',
                'words_count': 10000 * index}

    def test02_insert(self):
        with VaultFreezer() as _:
            response = self.cli.post(f'/db/collection/{self.collection_name}', body={
                'document': [self.__create_doc(i + 1) for i in range(2)]
            })
            RA(response).assert_status(HttpCode.FORBIDDEN)

        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            'document': [self.__create_doc(i+1) for i in range(2)]
        })

        RA(response).assert_status(201)
        self.assertEqual(len(RA(response).body().get('inserted_ids', list)), 2)

    def test02_insert_with_options(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            'document': [self.__create_doc(i+3) for i in range(3)],
            "options": {"bypass_document_validation": False, "ordered": True}
        })

        RA(response).assert_status(201)
        self.assertEqual(len(RA(response).body().get('inserted_ids', list)), 3)

    def test02_insert_with_timestamp(self):
        # insert a new document with timestamp=True
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            "document": [{"author": "timestamp_default", "title": "Eve for Dummies1", "words_count": 10000}]
        })
        RA(response).assert_status(201)
        # check if the inserted document contains two new fields: created, modified.
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"timestamp_default"}&skip=0')
        RA(response).assert_status(200)
        items = RA(response).body().get('items', list)
        self.assertEqual(len(items), 1)
        DictAsserter(**items[0]).assert_true('created', int)
        DictAsserter(**items[0]).assert_true('modified', int)

        # insert a new document with timestamp=False
        response = self.cli.post(f'/db/collection/{self.collection_name}', body={
            "document": [{"author": "timestamp_false", "title": "Eve for Dummies1", "words_count": 10000}],
            "options": {"timestamp": False}
        })
        RA(response).assert_status(201)
        # check if the inserted document contains two new fields: created, modified.
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"timestamp_false"}')
        RA(response).assert_status(200)
        items = RA(response).body().get('items', list)
        self.assertEqual(len(items), 1)
        self.assertTrue('created' not in items[0])
        self.assertTrue('modified' not in items[0])

    def test02_insert_with_invalid_parameter(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}')
        RA(response).assert_status(400)

    def test03_update(self):
        with VaultFreezer() as _:
            response = self.cli.patch(f'/db/collection/{self.collection_name}', body={
                "filter": {"author": "timestamp_default"},
                "update": {"$set": {"title": "Eve for Dummies1_1"}},
            })
            RA(response).assert_status(HttpCode.FORBIDDEN)

        response = self.cli.patch(f'/db/collection/{self.collection_name}', body={
            "filter": {"author": "timestamp_default"},
            "update": {"$set": {"title": "Eve for Dummies1_1"}},
        })
        RA(response).assert_status(200)
        RA(response).body().assert_equal('matched_count', 1)

    def test03_update_with_options(self):
        response = self.cli.patch(f'/db/collection/{self.collection_name}', body={
            "filter": {"author": "timestamp_false"},
            "update": {"$set": {"title": "Eve for Dummies1_1"}},
            "options": {"upsert": False, "bypass_document_validation": False}
        })
        RA(response).assert_status(200)
        RA(response).body().assert_equal('matched_count', 1)

    def test03_update_with_invalid_parameter(self):
        response = self.cli.patch(f'/db/collection/{self.collection_name}')
        RA(response).assert_status(400)

    def test03_update_with_updateone(self):
        def update(count):
            response = self.cli.patch(f'/db/collection/{self.collection_name}?updateone=true', body={
                "filter": {"author": "Alice", "title": "The Metrix 2"},
                "update": {"$set": {"words_count": count}}
            })
            RA(response).assert_status(200)
            RA(response).body().assert_equal('matched_count', 1)
        update(20200)  # update
        update(20000)  # update back

    def test03_update_with_insert_if_not_exists(self):
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
            "filter": {"author": "insert_if_not_exists"},
            "update": {"$setOnInsert": {"title": "Eve for Dummies4"}},
            "options": {"upsert": True, "bypass_document_validation": True}
        })
        RA(response).assert_status(200)
        RA(response).body().assert_equal('modified_count', 0)
        RA(response).body().assert_true('upserted_id', str)

        # check if the inserted document exists
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"insert_if_not_exists"}')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 1)

    def test04_count(self):
        with VaultFreezer() as _:
            response = self.cli.post(f'/db/collection/{self.collection_name}?op=count', body={
                "filter": {"author": "Alice"}
            })
            RA(response).assert_status(HttpCode.CREATED)

        response = self.cli.post(f'/db/collection/{self.collection_name}?op=count', body={
            "filter": {"author": "Alice"}
        })
        RA(response).assert_status(201)
        RA(response).body().assert_equal('count', 5)

    def test04_count_with_options(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}?op=count', body={
            "filter": {"author": "Alice"},
            "options": {"skip": 0, "limit": 3, "maxTimeMS": 1000000000}
        })
        RA(response).assert_status(201)
        RA(response).body().assert_equal('count', 3)

    def test04_count_with_invalid_parameter(self):
        response = self.cli.post(f'/db/collection/{self.collection_name}?op=count')
        RA(response).assert_status(400)

    def test05_find(self):
        with VaultFreezer() as _:
            response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"Alice"}')
            RA(response).assert_status(HttpCode.OK)

        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"Alice"}')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 5)

    def test05_find_with_options(self):
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"Alice"}&skip=0&limit=3')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 3)

    def test05_find_with_invalid_parameter(self):
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter=&skip=')
        RA(response).assert_status(400)

    def test06_query(self):
        with VaultFreezer() as _:
            response = self.cli.post(f'/db/query', body={
                "collection": self.collection_name,
                "filter": {"author": "Alice"}
            })
            RA(response).assert_status(HttpCode.CREATED)

        response = self.cli.post(f'/db/query', body={
            "collection": self.collection_name,
            "filter": {"author": "Alice"}
        })
        RA(response).assert_status(201)
        self.assertEqual(len(RA(response).body().get('items', list)), 5)

    def test06_query_with_gt_lt(self):
        response = self.cli.post(f'/db/query', body={
            "collection": self.collection_name,
            "filter": {"author": "Alice", "words_count": {"$gt": 0, "$lt": 50000}}
        })
        RA(response).assert_status(201)
        self.assertEqual(len(RA(response).body().get('items', list)), 4)

    def test06_query_with_options(self):
        response = self.cli.post(f'/db/query', body={
            "collection": self.collection_name,
            "filter": {"author": "Alice"},
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
            }
        })
        RA(response).assert_status(201)
        self.assertEqual(len(RA(response).body().get('items', list)), 3)

    def test06_query_with_sort(self):
        def query_with_sort(order: int):
            response = self.cli.post(f'/db/query', body={
                "collection": self.collection_name,
                "filter": {
                    "author": "Alice"
                },
                "options": {
                    'sort': [('_id', order)]  # sort with mongodb style.
                }})
            RA(response).assert_status(201)
            return RA(response).body().get('items', list)

        # query with sort: pymongo.ASCENDING
        items = query_with_sort(pymongo.ASCENDING)
        ids = list(map(lambda i: str(i['_id']), items))
        self.assertTrue(all(ids[i] <= ids[i+1] for i in range(len(ids) - 1)))

        # query with sort: pymongo.DESCENDING
        items = query_with_sort(pymongo.DESCENDING)
        ids = list(map(lambda i: str(i['_id']), items))
        self.assertTrue(all(ids[i] >= ids[i + 1] for i in range(len(ids) - 1)))

    def test06_query_with_invalid_parameter(self):
        response = self.cli.post(f'/db/query')
        RA(response).assert_status(400)

    def test07_delete(self):
        with VaultFreezer() as _:
            response = self.cli.delete(f'/db/collection/{self.collection_name}?deleteone=true', body={
                "filter": {"author": "Alice"}
            }, is_json=True)
            RA(response).assert_status(HttpCode.FORBIDDEN)

        # delete one
        response = self.cli.delete(f'/db/collection/{self.collection_name}?deleteone=true', body={
            "filter": {"author": "Alice"}
        }, is_json=True)
        RA(response).assert_status(204)

        # Remain 4
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"Alice"}')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 4)

        # delete many
        response = self.cli.delete(f'/db/collection/{self.collection_name}', body={
            "filter": {"author": "Alice"}
        }, is_json=True)
        RA(response).assert_status(204)

        # Remain 0
        response = self.cli.get(f'/db/{self.collection_name}' + '?filter={"author":"Alice"}')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 0)

    def test07_delete_with_invalid_parameter(self):
        response = self.cli.delete(f'/db/collection/{self.collection_name}')
        RA(response).assert_status(400)

    def test08_delete_collection_with_not_found(self):
        response = self.cli.delete(f'/db/{self.name_not_exist}')
        RA(response).assert_status(404)

    def test08_delete_collection(self):
        response = self.cli.delete(f'/db/{self.collection_name}')
        RA(response).assert_status(204)


if __name__ == '__main__':
    unittest.main()
