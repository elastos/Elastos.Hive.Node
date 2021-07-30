# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
from src.utils.http_response import hive_restful_response, hive_stream_response


class IpfsFiles:
    def __init__(self):
        pass

    @hive_restful_response
    def upload_file(self, path):
        pass

    @hive_stream_response
    def download_file(self, path):
        pass

    @hive_restful_response
    def delete_file(self, path):
        pass

    @hive_restful_response
    def move_file(self, src_path, dst_path):
        pass

    @hive_restful_response
    def copy_file(self, src_path, dst_path):
        pass

    @hive_restful_response
    def list_folder(self, path):
        pass

    @hive_restful_response
    def get_properties(self, path):
        pass

    @hive_restful_response
    def get_hash(self, path):
        pass
