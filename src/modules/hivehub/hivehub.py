# -*- coding: utf-8 -*-

"""
The entrance for hive_hub module.
"""
from bson import ObjectId

from src.utils.db_client import cli
from src.utils_v1.constants import DID_INFO_DB_NAME

HIVE_HUB_NODES = 'hive_hub_nodes'


class HiveHub:
    def __init__(self):
        pass

    def get_nodes(self, nid, owner_did):
        col_filter = {}
        if nid:
            col_filter['_id'] = ObjectId(nid)
        if owner_did:
            col_filter['owner_did'] = owner_did
        nodes = cli.find_many_origin(DID_INFO_DB_NAME, HIVE_HUB_NODES, col_filter,
                                     create_on_absence=True, throw_exception=False)

        def node_mapper(n):
            id_ = n.pop('_id')
            n['nid'] = str(id_)
            return n

        return {
            'nodes': list(map(node_mapper, nodes))
        }

    def add_node(self, node):
        return cli.insert_one_origin(DID_INFO_DB_NAME, HIVE_HUB_NODES, node,
                                     create_on_absence=True, is_extra=False)

    def remove_node(self, nid):
        cli.delete_one_origin(DID_INFO_DB_NAME, HIVE_HUB_NODES, {'_id': ObjectId(nid)}, is_check_exist=False)
