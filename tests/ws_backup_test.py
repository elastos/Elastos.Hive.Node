# -*- coding: utf-8 -*-

"""
Testing file for the ws-backup module.
"""
import unittest

from tests import init_test


class WsBackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()


if __name__ == '__main__':
    unittest.main()
