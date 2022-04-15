# -*- coding: utf-8 -*-

"""
Testing file for the about module.
"""
import json
import unittest

from src.utils.did.did_wrapper import Presentation
from tests.utils.http_client import HttpClient
from tests import init_test


class AboutTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')

    def test01_get_version(self):
        response = self.cli.get(f'/about/version', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('major' in response.json())

    def test01_get_node_version(self):
        response = self.cli.get(f'/node/version', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('major' in response.json())

    def test02_get_commit_id(self):
        response = self.cli.get(f'/about/commit_id', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('commit_id' in response.json())

    def test02_get_node_commit_id(self):
        response = self.cli.get(f'/node/commit_id', need_token=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('commit_id' in response.json())

    def test03_get_node_info(self):
        response = self.cli.get(f'/node/info')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('service_did'))
        self.assertTrue(response.json().get('owner_did'))
        self.verify_ownership_presentation(response.json().get('ownership_presentation'))
        self.assertTrue(response.json().get('version'))
        self.assertTrue(response.json().get('last_commit_id'))

    def verify_ownership_presentation(self, presentation: any):
        if type(presentation) is not dict:
            self.assertTrue(False, 'the ownership presentation is invalid.')
        presentation_str = json.dumps(presentation)
        vp = Presentation.from_json(presentation_str)
        self.assertTrue(vp.is_valid())


if __name__ == '__main__':
    unittest.main()
