import typing
import unittest


class DictAsserter(unittest.TestCase):
    def __init__(self, data: typing.Any):
        super().__init__()
        self.assertIsInstance(data, dict)
        self.data = data

    def check_dict(self, name) -> 'DictAsserter':
        """ check the member is dict and return member's asserter """
        self.assertIn(name, self.data)
        self.assertIsInstance(self.data[name], dict)
        return DictAsserter(self.data[name])

    def get_str(self, name):
        self.assertIn(name, self.data)
        self.assertIsInstance(self.data[name], str)
        return self.data[name]

    def get_int(self, name):
        self.assertIn(name, self.data)
        self.assertIsInstance(self.data[name], int)
        return self.data[name]

    def get_list(self, name):
        self.assertIn(name, self.data)
        self.assertIsInstance(self.data[name], list)
        return self.data[name]

    def contain_dicts(self, names):
        self.assertTrue(all([name in self.data and isinstance(self.data[name], dict) for name in names]))
