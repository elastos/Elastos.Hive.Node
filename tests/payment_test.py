# -*- coding: utf-8 -*-

"""
Testing file for payment module.
"""

import unittest

from tests.utils.http_client import HttpClient, TestConfig
from tests import init_test


class PaymentTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2/payment')

    def test01_get_version(self):
        response = self.cli.get('/version')
        self.assertEqual(response.status_code, 200)
