# -*- coding: utf-8 -*-

"""
The entrance for backup module.
"""
from src.utils.http_response import hive_restful_response, NotImplementedException


class Backup:
    def __init__(self):
        pass

    @hive_restful_response
    def get_state(self):
        pass

    @hive_restful_response
    def backup(self, target_node):
        pass

    @hive_restful_response
    def restore(self, source_node):
        pass

    @hive_restful_response
    def promotion(self):
        raise NotImplementedException()
