# -*- coding: utf-8 -*-

"""
hive_hub module to save hive node list in hive hub website.
"""
from flask_restful import Resource

from src.utils.http_request import RV
from src.modules.hivehub.hivehub import HiveHub


class GetNodes(Resource):
    def __init__(self):
        self.hivehub = HiveHub()

    def get(self):
        """ query nodes by nid(_id) or owner_did

        return: {
            "nodes": [{
                "nid": "jlaksjdflkjasdlkfj001",
                "name": "hive node 节点A",
                "created": "2021-11-09 21:00:32",
                "ip": "192.115.24.2",
                "owner_did": owner_did,
                "area": "加拿大 安大略省 多伦多市",
                "email": "1234456789@gamil.com",
                "url": hive1_url,
                "remark": <remark str>
            }, {
                "nid": "jlaksjdflkjasdlkfj002",
                "name": "hive node 节点B",
                "created": "2021-11-09 21:00:32",
                "ip": "192.115.24.2",
                "owner_did": "did:elastos:srgsve5h5yvnwi5yh4hyg2945hvwq0tq",
                "area": "加拿大 安大略省 多伦多市",
                "email": "1234456789@gamil.com",
                "url": hive1_url,
                "remark": <remark str>
            }]
        }

        """

        nid, owner_did = RV.get_args().get_opt('nid', str, ''), RV.get_args().get_opt('owner_did', str, '')
        return self.hivehub.get_nodes(nid, owner_did)


class AddNode(Resource):
    def __init__(self):
        self.hivehub = HiveHub()

    def post(self):
        """ Add node by `node` document

        example: {
            "node": {
                "nid": "jlaksjdflkjasdlkfj001",
                "name": "hive node 节点A",
                "created": "2021-11-09 21:00:32",
                "ip": "192.115.24.2",
                "owner_did": owner_did,
                "area": "加拿大 安大略省 多伦多市",
                "email": "1234456789@gamil.com",
                "url": hive1_url,
                "remark": <remark str>
            }
        }
        """

        node = RV.get_body().get('node', dict)
        return self.hivehub.add_node(node)
