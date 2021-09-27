# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
import logging
import shutil
from pathlib import Path

from src import hive_setting
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.constants import VAULT_ACCESS_WR, VAULT_ACCESS_R, DID_INFO_DB_NAME
from src.utils_v1.payment.vault_service_manage import inc_vault_file_use_storage_byte
from src.utils.consts import COL_IPFS_FILES, DID, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, \
    COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_IPFS_CID, COL_IPFS_CID_REF, CID, COUNT, CREATE_TIME, MODIFY_TIME
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
        Delete a file from the vault.
        1. Remove the cached file in local filesystem;
        2. Unpin the file data from corresponding IPFS node.
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

        file_path = fm.ipfs_get_file_path(did, app_did, path)
        if file_path.exists():
            file_path.unlink()

        self.delete_file_metadata(did, app_did, path, doc[COL_IPFS_FILES_IPFS_CID])
        inc_vault_file_use_storage_byte(did, 0 - doc[SIZE])

    @hive_restful_response
    def move_file(self, src_path, dst_path):
        if not src_path or not dst_path:
            raise InvalidParameterException()
        elif src_path == dst_path:
            raise InvalidParameterException(msg='The source filename and destination filename must not be same.')

        return self.move_file_really(src_path, dst_path)

    @hive_restful_response
    def copy_file(self, src_path, dst_path):
        if not src_path or not dst_path:
            raise InvalidParameterException()
        elif src_path == dst_path:
            raise InvalidParameterException(msg='The source filename and destination filename must not be same.')

        return self.move_file_really(src_path, dst_path, True)

    @hive_restful_response
    def list_folder(self, path):
        """
        List the files under the specific directory.
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
            raise InvalidParameterException(f'The directory {path} is not exist.')
        return {
            'value': list(map(lambda d: self._get_list_file_info_by_doc(d), docs))
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
        # remove the existing cache file.
        file_path = fm.ipfs_get_file_path(did, app_did, path)
        if file_path.exists():
            file_path.unlink()
        else:
            fm.create_dir(file_path.parent)

        # upload to the temporary file and then to IPFS node.
        temp_file = gene_temp_file_name()
        fm.write_file_by_request_stream(temp_file)

        # insert or update file metadata.
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one(did, app_did, COL_IPFS_FILES, col_filter, is_create=True, is_raise=False)
        if not doc:
            self.add_file_to_metadata(did, app_did, path, temp_file)
        else:
            self.update_file_metadata(did, app_did, path, temp_file, doc)

        # set temporary file as cache.
        shutil.move(temp_file.as_posix(), file_path.as_posix())

    def add_file_to_metadata(self, did, app_did, rel_path: str, file_path: Path):
        cid = fm.ipfs_upload_file_from_path(file_path)
        file_doc = {
            DID: did,
            APP_DID: app_did,
            COL_IPFS_FILES_PATH: rel_path,
            COL_IPFS_FILES_SHA256: fm.get_file_content_sha256(file_path),
            COL_IPFS_FILES_IS_FILE: True,
            SIZE: file_path.stat().st_size,
            COL_IPFS_FILES_IPFS_CID: cid,
        }
        self.increase_refcount_cid(cid)
        result = cli.insert_one(did, app_did, COL_IPFS_FILES, file_doc, is_create=True)
        inc_vault_file_use_storage_byte(did, file_doc[SIZE])
        logging.info(f'[ipfs-files] Add a new file {rel_path}')

    def update_file_metadata(self, did, app_did, rel_path: str, file_path: Path, old_doc=None):
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: rel_path}
        if not old_doc:
            old_doc = cli.find_one(did, app_did, COL_IPFS_FILES, col_filter, is_create=True, is_raise=False)
            if not old_doc:
                logging.error(f'The file {rel_path} does not exist. Update can not be done.')
                return

        # check if the same file.
        sha256 = fm.get_file_content_sha256(file_path)
        size = file_path.stat().st_size
        cid = fm.ipfs_upload_file_from_path(file_path)
        if size == old_doc[SIZE] and sha256 == old_doc[COL_IPFS_FILES_SHA256] \
                and cid == old_doc[COL_IPFS_FILES_IPFS_CID]:
            logging.info(f'The file {rel_path} is same, no need update.')
            return

        # do update really.
        if cid != old_doc[COL_IPFS_FILES_IPFS_CID]:
            self.increase_refcount_cid(cid)
        update = {'$set': {COL_IPFS_FILES_SHA256: sha256,
                           SIZE: size,
                           COL_IPFS_FILES_IPFS_CID: cid}}
        result = cli.update_one(did, app_did, COL_IPFS_FILES, col_filter, update, is_extra=True)
        if cid != old_doc[COL_IPFS_FILES_IPFS_CID]:
            self.decrease_refcount_cid(old_doc[COL_IPFS_FILES_IPFS_CID])
        logging.info(f'[ipfs-files] Update an existing file {rel_path}')

    def delete_file_metadata(self, did, app_did, rel_path, cid):
        col_filter = {DID: did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: rel_path}
        result = cli.delete_one(did, app_did, COL_IPFS_FILES, col_filter, is_check_exist=False)
        if result['deleted_count'] > 0:
            self.decrease_refcount_cid(cid)
        logging.info(f'[ipfs-files] Remove an existing file {rel_path}')

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
        file_path = fm.ipfs_get_file_path(did, app_did, path)
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
            raise AlreadyExistsException(msg=f'Destination file {dst_path} exists.')

        full_src_path = fm.ipfs_get_file_path(did, app_did, src_path)
        full_dst_path = fm.ipfs_get_file_path(did, app_did, dst_path)
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
            self.increase_refcount_cid(src_doc[COL_IPFS_FILES_IPFS_CID])
            cli.insert_one(did, app_did, COL_IPFS_FILES, file_doc)
            inc_vault_file_use_storage_byte(did, src_doc[SIZE])
        else:
            cli.update_one(did, app_did, COL_IPFS_FILES, src_filter,
                           {'$set': {COL_IPFS_FILES_PATH: dst_path}}, is_extra=True)
        return {
            'name': dst_path
        }

    def _get_list_file_info_by_doc(self, file_doc):
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

    def get_ipfs_file_access_url(self, metadata):
        return f'{hive_setting.IPFS_PROXY_URL}/ipfs/{metadata[COL_IPFS_FILES_IPFS_CID]}'

    def increase_refcount_cid(self, cid, count=1):
        if not cid:
            logging.error(f'CID must be provided for increase.')
            return

        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: cid}, is_raise=False)
        if not doc:
            doc = {
                CID: cid,
                COUNT: count
            }
            cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, doc, is_create=True)
        else:
            self._update_refcount_cid(cid, doc[COUNT] + count)

    def decrease_refcount_cid(self, cid, count=1):
        if not cid:
            logging.error(f'CID must exist for decrease.')
            return

        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: cid}, is_raise=False)
        if not doc:
            fm.ipfs_unpin_cid(cid)
            return
        if doc[COUNT] <= count:
            cli.delete_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: cid}, is_check_exist=False)
            fm.ipfs_unpin_cid(cid)
        else:
            self._update_refcount_cid(cid, doc[COUNT] - count)

    def _update_refcount_cid(self, cid, count):
        col_filter = {CID: cid}
        update = {'$set': {
            COUNT: count,
        }}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, col_filter, update, is_extra=True)
