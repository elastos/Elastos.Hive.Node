# -*- coding: utf-8 -*-

"""
Testing file for database module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


@unittest.skip
class DatabaseTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient('http://localhost:5000/api/v2/vault')
        self.collection_name = 'database_test'

    def test01_create_collection(self):
        response = self.cli.put(f'/db/collections/{self.collection_name}')
        self.assertTrue(response.status_code in [200, 201])
        self.assertEqual(response.json().get('name'), self.collection_name)

    def test02_delete_collection(self):
        response = self.cli.delete(f'/db/{self.collection_name}')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
