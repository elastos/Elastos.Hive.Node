import unittest

from bson import ObjectId

from src.modules.database.mongodb_client import MongodbCollection
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import RequestData


@unittest.skip
class MongodbClientTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

    def test01_convert_oid(self):
        name, gid = 'Fred', '5f497bb83bd36ab235d82e6a'
        gid_dict = {'$oid': gid}
        doc = {
            'name': name,
            'gid': gid_dict,
            'items': [{'name': name, 'gid': gid_dict}],
            'items2': ({'name': name, 'gid': gid_dict}, ),
            'items3': {
                'name': name,
                'gid': gid_dict,
                'items4': {'name': name, 'gid': gid_dict},
                'items5': {'name': name, 'gid': gid_dict, 'items6': {
                    'name': name,
                    'gid': gid_dict
                }}
            },
        }
        doc2 = MongodbCollection(None, is_management=False).convert_oid(doc)

        def assert_gid_dict(value):
            self.assertEqual(type(value), ObjectId)
            self.assertEqual(str(value), gid)

        self.assertEqual(doc2['name'], name)
        assert_gid_dict(doc2['gid'])
        self.assertEqual(doc2['items'][0]['name'], name)
        assert_gid_dict(doc2['items'][0]['gid'])
        self.assertEqual(doc2['items2'][0]['name'], name)
        assert_gid_dict(doc2['items2'][0]['gid'])
        self.assertEqual(doc2['items3']['name'], name)
        assert_gid_dict(doc2['items3']['gid'])
        self.assertEqual(doc2['items3']['items4']['name'], name)
        assert_gid_dict(doc2['items3']['items4']['gid'])
        self.assertEqual(doc2['items3']['items5']['name'], name)
        assert_gid_dict(doc2['items3']['items5']['gid'])
        self.assertEqual(doc2['items3']['items5']['items6']['name'], name)
        assert_gid_dict(doc2['items3']['items5']['items6']['gid'])


@unittest.skip
class RequestValidatorTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

    def test01_rv(self):
        doc = {
            "executable": {
                "type": "find",
                "name": "find_messages",
                "body": {
                    "collection": "messages",
                    "filter": {"group_id": "$params.group_id"},
                    "options": {"projection": {"_id": False}, "limit": 100}
                }}}

        body = RequestData(**doc)

        # get
        self.assertEqual(body.get('executable').get('type', str), 'find')
        self.assertEqual(body.get('executable').get('body').get('collection', str), 'messages')

        # get optional
        self.assertFalse(body.get_opt('condition', dict, {}).get_opt('filter'))
        self.assertTrue(body.get('executable').get('body').get_opt('options').get_opt('limit', int), 100)

        # validate and validate_opt
        body.validate('executable')
        body.get('executable').validate('body')
        body.get('executable').validate_opt('output')
        body.get('executable').get('body').validate('collection', str)
        body.get('executable').get('body').get_opt('options').validate_opt('skip')
        with self.assertRaises(InvalidParameterException):
            body.validate('condition')
        with self.assertRaises(InvalidParameterException):
            body.get('executable').validate('output')
        with self.assertRaises(InvalidParameterException):
            body.get('executable').get('body').get_opt('options').validate('skip')

        self.assertTrue(True)
