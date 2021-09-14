# -*- coding: utf-8 -*-

"""
Testing file for about module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class AboutTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/about')

    def test01_get_version(self):
        response = self.cli.get(f'/version', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('major' in response.json())

    def test02_get_commit_id(self):
        response = self.cli.get(f'/commit_id', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('commit_id' in response.json())


if __name__ == '__main__':
    unittest.main()
