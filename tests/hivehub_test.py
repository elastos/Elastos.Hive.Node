import unittest
from datetime import datetime

from tests import init_test, RA
from tests.utils.http_client import HttpClient
from tests.utils.resp_asserter import DictAsserter


class AboutTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/hivehub')

    def test01_all(self):
        node_name = f'hive node name {datetime.now().timestamp()}'
        owner_did = f'owner_id_{datetime.now().timestamp()}'
        node_info = {
            "node": {
                "name": node_name,
                "created": "2021-11-09 21:00:32",
                "ip": "192.115.24.2",
                "owner_did": owner_did,
                "area": "加拿大 安大略省 多伦多市",
                "email": "1234456789@gamil.com",
                "url": "https://hive-testnet1.trinity-tech.io",
                "remark": "hive-testnet1 node"
            }
        }

        def get_nodes():
            r = self.cli.get(f'/nodes?owner_did={owner_did}', need_token=False)
            RA(r).assert_status(200)
            return RA(r).body().get('nodes', list)

        # get exists nodes number
        exists_count = len(get_nodes())

        # add a new node.
        response = self.cli.post(f'/node', node_info, need_token=False)
        RA(response).assert_status(201)

        # get added one.
        items = get_nodes()
        self.assertEqual(len(items), 1)
        DictAsserter(**items[0]).assert_equal('name', node_name)
        DictAsserter(**items[0]).assert_equal('owner_did', owner_did)

        # remove node
        response = self.cli.delete(f'/node?nid={DictAsserter(**items[0]).get("nid", str)}', need_token=False)
        RA(response).assert_status(204)

        # check added one
        items = get_nodes()
        self.assertEqual(len(items), 0)

        # make sure the collection did not change
        self.assertEqual(len(get_nodes()), exists_count)


if __name__ == '__main__':
    unittest.main()
