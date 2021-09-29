# -*- coding: utf-8 -*-

"""
Testing file for the auth module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class AuthTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')

    def test01_signin_invalid_parameter(self):
        response = self.cli.post(f'/did/signin', body=dict(), need_token=False)
        self.assertEqual(response.status_code, 400)

    def test02_auth_invalid_parameter(self):
        response = self.cli.post(f'/did/auth', body=dict(), need_token=False)
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
