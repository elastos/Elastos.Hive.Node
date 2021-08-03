# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
from hive.util.constants import VAULT_ACCESS_WR, DID_INFO_DB_NAME, VAULT_ACCESS_R
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.consts import COL_IPFS_FILES, DID, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, \
    COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_IPFS_CID
from src.utils.db_client import cli
from src.utils.file_manager import fm
from src.utils.http_exception import InvalidParameterException, FileNotFoundException
from src.utils.http_response import hive_restful_response, hive_stream_response
from src.utils.node_settings import st_get_ipfs_cache_path


class IpfsFiles:
    def __init__(self):
        pass

    @hive_restful_response
    def upload_file(self, path):
        if not path:
            raise InvalidParameterException()

        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        self.upload_file_by_did(did, app_did, path)
        return {
            'name': path
        }

    @hive_stream_response
    def download_file(self, path):
        if not path:
            raise InvalidParameterException()

        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        return self.download_file_by_did(did, app_did, path)

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

    def upload_file_by_did(self, did, app_did, path):
        """
        Upload file really.
            1. generate the local file name and save the content to local.
            2. add file document to the vault_files collection or update doc by remove cid.
            3. return None.
            4. run a timely script to upload file to IPFS node and update the relating file documents.
        :param did: the user did
        :param app_did: the application did
        :param path: the file relative path, not None
        :return: None
        """
        file_path = fm.ipfs_get_file_path(did, path)
        fm.write_file_by_request_stream(file_path)
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_FILES, col_filter, is_create=True, is_raise=False)
        if not doc:
            # not exists, add new one.
            file_doc = {
                DID: did,
                APP_DID: app_did,
                COL_IPFS_FILES_PATH: path,
                COL_IPFS_FILES_SHA256: fm.get_file_content_sha256(file_path),
                COL_IPFS_FILES_IS_FILE: True,
                SIZE: file_path.stat().st_size,
                COL_IPFS_FILES_IPFS_CID: None,
            }
            result = cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_FILES, file_doc, is_create=True)
        else:
            # exists, just remove cid for uploading the file to IPFS node later.
            result = cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_FILES,
                                           col_filter, {'$set': {COL_IPFS_FILES_IPFS_CID: None}}, is_extra=True)

    def download_file_by_did(self, did, app_did, path):
        """
        Download file by did.
        1. check file caches.
        2. download file from IPFS to files cache if no cache.
        3. return the file content as the response.
        :param did: The user did.
        :param app_did:
        :param path:
        :return:
        """
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_FILES, col_filter)
        if not doc:
            raise FileNotFoundException(msg=f'Can not find the file with path: {path}')
        file_path = fm.ipfs_get_file_path(did, path)
        if not file_path.exists():
            fm.ipfs_download_file_to_path(doc[COL_IPFS_FILES_IPFS_CID], file_path)
        return fm.get_response_by_file_path(file_path)
