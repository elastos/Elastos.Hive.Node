import unittest


class DictAsserter(unittest.TestCase, dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        unittest.TestCase.__init__(self)

    def get(self, key, t=dict):
        self.assertIn(key, self)
        self.assertIsInstance(self[key], t)
        return DictAsserter(**self[key]) if t == dict else self[key]

    def assert_type(self, key, t=dict):
        self.assertIn(key, self)
        self.assertIsInstance(self[key], t)

    def assert_equal(self, key, dst_value):
        # can not compare with None
        self.assertIsNotNone(dst_value, 'assert_equal: "dst_value" should not be None')
        self.assertIn(key, self)
        # same type
        self.assert_type(key, type(dst_value))
        # same value
        if isinstance(dst_value, float):
            # float checking
            self.assertLess(abs(self[key] - dst_value), abs(dst_value * 0.01))
        else:
            self.assertEqual(self[key], dst_value)

    def assert_in(self, key, targets: list):
        self.assertIsNotNone(targets, 'assert_equal: "targets" should not be None')
        self.assertIn(key, self)
        self.assertTrue(self[key] in targets)

    def assert_less(self, key, dst_value):
        self.assertIsNotNone(dst_value, 'assert_equal: "dst_value" should not be None')
        self.assert_type(key, type(dst_value))
        self.assertLess(self[key], dst_value)

    def assert_greater(self, key, dst_value):
        self.assertIsNotNone(dst_value, 'assert_equal: "dst_value" should not be None')
        self.assert_type(key, type(dst_value))
        self.assertGreater(self[key], dst_value)

    def assert_true(self, key, t=dict):
        self.assert_type(key, t)
        self.assertTrue(self[key])

    def __repr__(self):
        return dict.__repr__(self)

    def __str__(self):
        return dict.__str__(self)


class RA(unittest.TestCase):
    """ Response Asserter
    Helper class to assert the response values, like:

        - status
        - the body in JSON type
        - the keys in body: exists, type, etc.
        - the values in body: equal, true, etc.

    Examples:

        RA(response).assert_status(200)
        RA(response).assert_status(200, 455)

        RA(response).body().get('executable_find')
        RA(response).body().get('inserted_ids', list)
        RA(response).body().get('executable_find').get('items', list)

        RA(response).body().assertType('executable_find')
        RA(response).body().get_dict_asserter('executable_find').assert_type('total', int)
        RA(response).body().get_dict_asserter('executable_find').assert_type('items', list)
        RA(response).body().get_dict_asserter('executable_find').assert_equal('total', 9)  # assert type and value

    """

    def __init__(self, response):
        super().__init__()
        self.response = response

    def assert_status(self, *args):
        self.assertIn(self.response.status_code, args)

    def body(self):
        self.assertIsInstance(self.response.json(), dict)
        return DictAsserter(**self.response.json())

    def text_equal(self, dst_value):
        self.assertIsInstance(dst_value, str)
        self.assertEqual(self.response.text, dst_value)
