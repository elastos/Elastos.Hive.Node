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
from src.utils_v1.payment.vault_service_manage import update_used_storage_for_files_data
from src.utils.consts import COL_IPFS_FILES, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, \
    COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_IPFS_CID, COL_IPFS_CID_REF, CID, COUNT, USR_DID
from src.utils.db_client import cli
from src.utils.did_auth import check_auth_and_vault
from src.utils.file_manager import fm
from src.utils.http_exception import InvalidParameterException, FileNotFoundException, AlreadyExistsException
from src.utils.http_response import hive_restful_response, hive_stream_response


class IpfsFiles:
    def __init__(self):
        """
        IPFS node is being used to store immutable block data (files):
        1. Each user_did/app_did has the sandboxing to cache application data;
        2. Each user_did/app_did has the mongodb collection to manage the metadata on the block data on IPFS node;
        3. Once a block data (usually file) has been uploaded to hive node, it would be cached on local filesystem
        first, afterwards it also would be uploaded and pined to the paired IPFS node.
        4. The CID to the block data on IPFS would be managed as the field of metadata in the collection.
        """
        pass

    @hive_restful_response
    def upload_file(self, path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        self.upload_file_with_path(user_did, app_did, path)
        return {
            'name': path
        }

    @hive_stream_response
    def download_file(self, path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        return self.download_file_with_path(user_did, app_did, path)

    @hive_restful_response
    def delete_file(self, path):
        """
        Delete a file from the vault.
        1. Remove the cached file in local filesystem;
        2. Unpin the file data from corresponding IPFS node.
        :param path:
        :return:
        """
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        self.delete_file_with_path(user_did, app_did, path)

    def delete_file_with_path(self, user_did, app_did, path):
        col_filter = {USR_DID: user_did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        doc = cli.find_one(user_did, app_did, COL_IPFS_FILES, col_filter, throw_exception=False)
        if not doc:
            return

        cache_file = fm.ipfs_get_cache_root(user_did) / doc[COL_IPFS_FILES_IPFS_CID]
        if cache_file.exists():
            cache_file.unlink()

        self.delete_file_metadata(user_did, app_did, path, doc[COL_IPFS_FILES_IPFS_CID])
        update_used_storage_for_files_data(user_did, 0 - doc[SIZE])

    @hive_restful_response
    def move_file(self, src_path, dst_path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        return self.move_copy_file(user_did, app_did, src_path, dst_path)

    @hive_restful_response
    def copy_file(self, src_path, dst_path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        return self.move_copy_file(user_did, app_did, src_path, dst_path, is_copy=True)

    @hive_restful_response
    def list_folder(self, path):
        """
        List the files under the specific directory.
        :param path: Empty means root folder.
        :return: File list.
        """
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        docs = self.list_folder_with_path(user_did, app_did, path)
        return {
            'value': list(map(lambda d: self._get_list_file_info_by_doc(d), docs))
        }

    def list_folder_with_path(self, user_did, app_did, path):
        col_filter = {USR_DID: user_did, APP_DID: app_did}
        if path:
            folder_path = path if path[len(path) - 1] == '/' else f'{path}/'
            col_filter[COL_IPFS_FILES_PATH] = {
                '$regex': f'^{folder_path}'
            }
        docs = cli.find_many(user_did, app_did, COL_IPFS_FILES, col_filter)
        if not docs and path:
            raise InvalidParameterException(f'The directory {path} is not exist.')
        return docs

    @hive_restful_response
    def get_properties(self, path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        metadata = self.get_file_metadata(user_did, app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'is_file': metadata[COL_IPFS_FILES_IS_FILE],
            'size': metadata[SIZE],
            'created': metadata['created'],
            'updated': metadata['modified'],
        }

    @hive_restful_response
    def get_hash(self, path):
        user_did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        metadata = self.get_file_metadata(user_did, app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'algorithm': 'SHA256',
            'hash': metadata[COL_IPFS_FILES_SHA256]
        }

    def upload_file_with_path(self, user_did, app_did, path: str):
        """
        The routine to process the file uploading:
            1. Receive the content of uploaded file and cache it a temp file;
            2. Add this file onto IPFS node and return with CID;
            3. Create a new metadata with the CID and store them as document;
            4. Cached the temp file to specific cache directory.

        :param user_did: the user did
        :param app_did: the application did
        :param path: the file relative path, not None
        :return: None
        """
        # upload to the temporary file and then to IPFS node.
        temp_file = gene_temp_file_name()
        fm.write_file_by_request_stream(temp_file)
        self.upload_file_from_local(user_did, app_did, path, temp_file)

    def upload_file_from_local(self, user_did, app_did, path: str, local_path: Path, only_import=False, **kwargs):
        # insert or update file metadata.
        doc = self.get_file_metadata(user_did, app_did, path, throw_exception=False)
        if not doc:
            cid = self.create_file_metadata(user_did, app_did, path, local_path,
                                            only_import=only_import, **kwargs)
        else:
            cid = self.update_file_metadata(user_did, app_did, path, local_path, doc,
                                            only_import=only_import, **kwargs)

        # set temporary file as cache.
        if cid:
            cache_file = fm.ipfs_get_cache_root(user_did) / cid
            if cache_file.exists():
                cache_file.unlink()
            if only_import:
                shutil.copy(local_path.as_posix(), cache_file.as_posix())
            else:
                shutil.move(local_path.as_posix(), cache_file.as_posix())

    def create_file_metadata(self, user_did, app_did, rel_path: str, file_path: Path, only_import=False, **kwargs):
        cid = fm.ipfs_upload_file_from_path(file_path)
        metadata = {
            USR_DID: user_did,
            APP_DID: app_did,
            COL_IPFS_FILES_PATH: rel_path,
            COL_IPFS_FILES_SHA256: fm.get_file_content_sha256(file_path),
            COL_IPFS_FILES_IS_FILE: True,
            SIZE: file_path.stat().st_size,
            COL_IPFS_FILES_IPFS_CID: cid,
        }
        self.increase_refcount_cid(cid)
        result = cli.insert_one(user_did, app_did, COL_IPFS_FILES, metadata, create_on_absence=True, **kwargs)
        if not only_import:
            update_used_storage_for_files_data(user_did, metadata[SIZE])
        logging.info(f'[ipfs-files] Add a new file {rel_path}')
        return cid

    def update_file_metadata(self, user_did, app_did, rel_path: str, file_path: Path,
                             existing_metadata=None, only_import=False, **kwargs):
        col_filter = {USR_DID: user_did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: rel_path}
        if not existing_metadata:
            existing_metadata = cli.find_one(user_did, app_did, COL_IPFS_FILES, col_filter, create_on_absence=True, throw_exception=False)
            if not existing_metadata:
                logging.error(f'The file {rel_path} metadata is not existed, impossible to be updated')
                return None

        # check the consistence between the new one and existing one.
        sha256 = fm.get_file_content_sha256(file_path)
        cid = fm.ipfs_upload_file_from_path(file_path)
        size = file_path.stat().st_size
        if size == existing_metadata[SIZE] and sha256 == existing_metadata[COL_IPFS_FILES_SHA256] \
                and cid == existing_metadata[COL_IPFS_FILES_IPFS_CID]:
            logging.info(f'The file {rel_path} metadata is consistent with existed one, skip updation')
            return None

        # update the metadata of new file.
        if cid != existing_metadata[COL_IPFS_FILES_IPFS_CID]:
            self.increase_refcount_cid(cid)
        updated_metadata = {'$set': {COL_IPFS_FILES_SHA256: sha256,
                            SIZE: size,
                            COL_IPFS_FILES_IPFS_CID: cid}}
        result = cli.update_one(user_did, app_did, COL_IPFS_FILES, col_filter, updated_metadata,
                                is_extra=True, **kwargs)

        ## dereference the existing cid to IPFS.
        if cid != existing_metadata[COL_IPFS_FILES_IPFS_CID]:
            self.decrease_refcount_cid(existing_metadata[COL_IPFS_FILES_IPFS_CID])

        if not only_import and size != existing_metadata[SIZE]:
            update_used_storage_for_files_data(user_did, size - existing_metadata[SIZE])

        logging.info(f'[ipfs-files] The existing file with {rel_path} has been updated')
        return cid

    def delete_file_metadata(self, user_did, app_did, rel_path, cid):
        col_filter = {USR_DID: user_did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: rel_path}
        result = cli.delete_one(user_did, app_did, COL_IPFS_FILES, col_filter, is_check_exist=False)
        if result['deleted_count'] > 0 and cid:
            self.decrease_refcount_cid(cid)
        logging.info(f'[ipfs-files] Remove an existing file {rel_path}')

    def download_file_with_path(self, user_did, app_did, path: str):
        """
        Download the target file with the following steps:
        1. Check target file already be cached, then just use this file, otherwise:
        2. Download file from IPFS to cache directory;
        3. Response to requrester with this cached file.

        :param user_did: The user did.
        :param app_did: The application did
        :param path:
        :return:
        """
        metadata = self.get_file_metadata(user_did, app_did, path)
        cached_file = fm.ipfs_get_cache_root(user_did) / metadata[COL_IPFS_FILES_IPFS_CID]
        if not cached_file.exists():
            fm.ipfs_download_file_to_path(metadata[COL_IPFS_FILES_IPFS_CID], cached_file)
        return fm.get_response_by_file_path(cached_file)

    def move_copy_file(self, user_did, app_did, src_path, dst_path, is_copy=False):
        """
        Move/Copy file with the following steps:
        1. Check source file existing and file with destination name existing. If not, then
        2. Move or copy file;
        3. Update metadata

        :param user_did:
        :param app_did:
        :param src_path: The path of the source file.
        :param dst_path: The path of the destination file.
        :param is_copy: True means copy file, else move.
        :return: Json data of the response.
        """
        src_filter = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: src_path}
        dst_filter = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: dst_path}
        src_doc = cli.find_one(user_did, app_did, COL_IPFS_FILES, src_filter)
        dst_doc = cli.find_one(user_did, app_did, COL_IPFS_FILES, dst_filter)
        if not src_doc:
            raise FileNotFoundException(msg=f'The source file {src_path} not found, impossible to move/copy.')
        if dst_doc:
            raise AlreadyExistsException(msg=f'A file with destnation name {dst_path} already exists, impossible to move/copy')

        if is_copy:
            metadata = {
                USR_DID: user_did,
                APP_DID: app_did,
                COL_IPFS_FILES_PATH: dst_path,
                COL_IPFS_FILES_SHA256: src_doc[COL_IPFS_FILES_SHA256],
                COL_IPFS_FILES_IS_FILE: True,
                SIZE: src_doc[SIZE],
                COL_IPFS_FILES_IPFS_CID: src_doc[COL_IPFS_FILES_IPFS_CID],
            }
            self.increase_refcount_cid(src_doc[COL_IPFS_FILES_IPFS_CID])
            cli.insert_one(user_did, app_did, COL_IPFS_FILES, metadata)
            update_used_storage_for_files_data(user_did, src_doc[SIZE])
        else:
            cli.update_one(user_did, app_did, COL_IPFS_FILES, src_filter,
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

    def get_file_metadata(self, user_did, app_did, path: str, throw_exception=True):
        col_filter = {USR_DID: user_did,
                      APP_DID: app_did,
                      COL_IPFS_FILES_PATH: path}
        metadata = cli.find_one(user_did, app_did, COL_IPFS_FILES, col_filter,
                                create_on_absence=True, throw_exception=throw_exception)
        if not metadata:
            if throw_exception:
                raise FileNotFoundException(msg=f'No file metadata with path: {path} found')
            return None
        return metadata

    def get_ipfs_file_access_url(self, metadata):
        return f'{hive_setting.IPFS_PROXY_URL}/ipfs/{metadata[COL_IPFS_FILES_IPFS_CID]}'

    def increase_refcount_cid(self, cid, count=1):
        if not cid:
            logging.error(f'CID must be provided for increase.')
            return

        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: cid},
                                  create_on_absence=True, throw_exception=False)
        if not doc:
            doc = {
                CID: cid,
                COUNT: count
            }
            cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, doc, create_on_absence=True)
        else:
            self._update_refcount_cid(cid, doc[COUNT] + count)

    def decrease_refcount_cid(self, cid, count=1):
        if not cid:
            logging.error(f'CID must exist for decrease.')
            return

        doc = cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: cid},
                                  create_on_absence=True, throw_exception=False)
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
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, col_filter, update,
                              create_on_absence=True, is_extra=True)
