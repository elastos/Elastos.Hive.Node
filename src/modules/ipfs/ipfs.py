# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
import shutil

from hive.util.constants import VAULT_ACCESS_WR, VAULT_ACCESS_R
from hive.util.payment.vault_service_manage import inc_vault_file_use_storage_byte
from src.utils.consts import COL_IPFS_FILES, DID, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, \
    COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_IPFS_CID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.file_manager import fm
from src.utils.http_exception import InvalidParameterException, FileNotFoundException, AlreadyExistsException
from src.utils.http_response import hive_restful_response, hive_stream_response


class IpfsFiles:
    def __init__(self):
        """
        Use IPFS node as the file storage.
        1. Every did has a local files cache.
        2. Every did/app_did has its own files collection.
        3. When uploading the file, cache it locally. Then upload to the IPFS node with the timed script.
        4. The files with same content is relating to the same CID of the IPFS node. So it can not be unpined in IPFS.
        """
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
        """
        Delete the file.
        1. remove the file in files cache.
        2. unpin the file in IPFS node.
        :param path:
        :return:
        """
        if not path:
            raise InvalidParameterException()

        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one(did, app_did, COL_IPFS_FILES, col_filter, is_raise=False)
        if not doc:
            return

        file_path = fm.ipfs_get_file_path(did, path)
        if file_path.exists():
            file_path.unlink()

        if doc[COL_IPFS_FILES_IPFS_CID]:
            # INFO: can not unpin file in the IPFS node because of CID maybe used for many files.
            #fm.ipfs_remove_file(doc[COL_IPFS_FILES_IPFS_CID])
            pass

        inc_vault_file_use_storage_byte(did, 0 - doc[SIZE])
        cli.delete_one(did, app_did, COL_IPFS_FILES, col_filter, is_check_exist=False)

    @hive_restful_response
    def move_file(self, src_path, dst_path):
        if not src_path or not dst_path:
            raise InvalidParameterException()
        elif src_path == dst_path:
            raise InvalidParameterException(msg='The source file and the destination file can not be the same.')

        return self.move_file_really(src_path, dst_path)

    @hive_restful_response
    def copy_file(self, src_path, dst_path):
        if not src_path or not dst_path:
            raise InvalidParameterException()
        elif src_path == dst_path:
            raise InvalidParameterException(msg='The source file and the destination file can not be the same.')

        return self.move_file_really(src_path, dst_path, True)

    @hive_restful_response
    def list_folder(self, path):
        """
        List the files recursively.
        :param path: Empty means root folder.
        :return: File list.
        """
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        col_filter = {DID: did, APP_DID: app_did}
        if path:
            folder_path = path if path[len(path) - 1] == '/' else f'{path}/'
            col_filter[COL_IPFS_FILES_PATH] = {
                '$regex': f'^{folder_path}'
            }
        docs = cli.find_many(did, app_did, COL_IPFS_FILES, col_filter)
        if not docs and path:
            raise InvalidParameterException(f'Can not find the folder {path}')
        return {
            'value': list(map(lambda d: self.get_list_file_info_by_doc(d), docs))
        }

    @hive_restful_response
    def get_properties(self, path):
        if not path:
            raise InvalidParameterException()

        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        doc = self.check_file_exists(did, app_did, path)

        return {
            'name': doc[COL_IPFS_FILES_PATH],
            'is_file': doc[COL_IPFS_FILES_IS_FILE],
            'size': doc[SIZE],
            'created': doc['created'],
            'updated': doc['modified'],
        }

    @hive_restful_response
    def get_hash(self, path):
        if not path:
            raise InvalidParameterException()

        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        doc = self.check_file_exists(did, app_did, path)

        return {
            'name': doc[COL_IPFS_FILES_PATH],
            'algorithm': 'SHA256',
            'hash': doc[COL_IPFS_FILES_SHA256]
        }

    def upload_file_by_did(self, did, app_did, path: str):
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
        doc = cli.find_one(did, app_did, COL_IPFS_FILES, col_filter, is_create=True, is_raise=False)
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
            result = cli.insert_one(did, app_did, COL_IPFS_FILES, file_doc, is_create=True)
            inc_vault_file_use_storage_byte(did, file_doc[SIZE])
        else:
            # exists, just remove cid for uploading the file to IPFS node later.
            result = cli.update_one(did, app_did, COL_IPFS_FILES,
                                    col_filter, {'$set': {COL_IPFS_FILES_IPFS_CID: None}}, is_extra=True)
            inc_vault_file_use_storage_byte(did, file_path.stat().st_size - doc[SIZE])

    def download_file_by_did(self, did, app_did, path: str):
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
        doc = self.check_file_exists(did, app_did, path)
        file_path = fm.ipfs_get_file_path(did, path)
        if not file_path.exists():
            fm.ipfs_download_file_to_path(doc[COL_IPFS_FILES_IPFS_CID], file_path)
        return fm.get_response_by_file_path(file_path)

    def move_file_really(self, src_path, dst_path, is_copy=False):
        """
        Move or copy file, not support directory.
        1. check the existence of the source file.
        2. move or copy file.
        3. update the source file document or insert a new one.
        :param src_path: The path of the source file.
        :param dst_path: The path of the destination file.
        :param is_copy: True means copy file, else move.
        :return: Json data of the response.
        """
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)

        src_filter = {DID: did, APP_DID: app_did, COL_IPFS_FILES_PATH: src_path}
        dst_filter = {DID: did, APP_DID: app_did, COL_IPFS_FILES_PATH: dst_path}
        src_doc = cli.find_one(did, app_did, COL_IPFS_FILES, src_filter)
        dst_doc = cli.find_one(did, app_did, COL_IPFS_FILES, dst_filter)
        if not src_doc:
            raise FileNotFoundException(msg=f'Source file {src_path} does not exist.')
        if dst_doc:
            raise AlreadyExistsException(msg=f'Destination file {src_path} exists.')

        full_src_path = fm.ipfs_get_file_path(did, src_path)
        full_dst_path = fm.ipfs_get_file_path(did, dst_path)
        if full_dst_path.exists():
            full_dst_path.unlink()
        if full_src_path.exists():
            if is_copy:
                shutil.copy2(full_src_path.as_posix(), full_dst_path.as_posix())
            else:
                shutil.move(full_src_path.as_posix(), full_dst_path.as_posix())

        if is_copy:
            file_doc = {
                DID: did,
                APP_DID: app_did,
                COL_IPFS_FILES_PATH: dst_path,
                COL_IPFS_FILES_SHA256: src_doc[COL_IPFS_FILES_SHA256],
                COL_IPFS_FILES_IS_FILE: True,
                SIZE: src_doc[SIZE],
                COL_IPFS_FILES_IPFS_CID: src_doc[COL_IPFS_FILES_IPFS_CID],
            }
            cli.insert_one(did, app_did, COL_IPFS_FILES, file_doc)
            inc_vault_file_use_storage_byte(did, src_doc[SIZE])
        else:
            cli.update_one(did, app_did, COL_IPFS_FILES, src_filter,
                           {'$set': {COL_IPFS_FILES_PATH: dst_path}}, is_extra=True)
        return {
            'name': dst_path
        }

    def get_list_file_info_by_doc(self, file_doc):
        return {
            'name': file_doc[COL_IPFS_FILES_PATH],
            'is_file': file_doc[COL_IPFS_FILES_IS_FILE],
            'size': file_doc[SIZE],
        }

    def check_file_exists(self, did, app_did, path: str):
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one(did, app_did, COL_IPFS_FILES, col_filter)
        if not doc:
            raise FileNotFoundException(msg=f'Can not find the file metadata with path: {path}')
        return doc
