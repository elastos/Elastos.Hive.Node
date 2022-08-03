# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
import logging
import shutil
from pathlib import Path

from flask import g

from src.modules.files.file_metadata import FileMetadataManager
from src.modules.files.ipfs_client import IpfsClient
from src.modules.files.local_file import LocalFile
from src.utils.consts import COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, COL_IPFS_FILES_IS_FILE, SIZE, COL_IPFS_FILES_IPFS_CID, COL_IPFS_FILES_IS_ENCRYPT, \
    COL_IPFS_FILES_ENCRYPT_METHOD
from src.utils.http_exception import FileNotFoundException, AlreadyExistsException
from src.modules.files.ipfs_cid_ref import IpfsCidRef
from src.modules.subscription.vault import VaultManager


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
        self.vault_manager = VaultManager()
        self.file_manager = FileMetadataManager()
        self.ipfs_client = IpfsClient()

    def upload_file(self, path, is_public: bool, script_name: str, is_encrypt: bool, encrypt_method: str):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        cid = self.upload_file_with_path(g.usr_did, g.app_did, path, is_encrypt, encrypt_method)

        # anonymous share to any users
        if is_public:
            from src.modules.scripting.scripting import Scripting
            Scripting().set_script_for_anonymous_file(script_name, path)

        return {
            'name': path,
            'cid': cid if is_public else ''
        }

    def download_file(self, path):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        return self.download_file_with_path(g.usr_did, g.app_did, path)

    def delete_file(self, path):
        """
        Delete a file from the vault.
        1. Remove the cached file in local filesystem;
        2. Unpin the file data from corresponding IPFS node.
        :param path:
        :return:

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        self.delete_file_with_path(g.usr_did, g.app_did, path, check_exist=True)

    def delete_file_with_path(self, user_did, app_did, path, check_exist=False):
        """ 'public' for v1 """
        try:
            metadata = self.file_manager.get_metadata(user_did, app_did, path)
        except FileNotFoundException as e:
            if check_exist:
                raise e
            else:
                return

        # do real remove
        LocalFile.remove_ipfs_cache_file(user_did, metadata[COL_IPFS_FILES_IPFS_CID])
        self.file_manager.delete_metadata(user_did, app_did, path, metadata[COL_IPFS_FILES_IPFS_CID])
        self.vault_manager.update_user_files_size(user_did, 0 - metadata[SIZE])

    def move_file(self, src_path, dst_path):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        return self.move_copy_file(g.usr_did, g.app_did, src_path, dst_path)

    def copy_file(self, src_path, dst_path):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        return self.move_copy_file(g.usr_did, g.app_did, src_path, dst_path, is_copy=True)

    def list_folder(self, path):
        """
        List the files under the specific directory.
        :param path: Empty means root folder.
        :return: File list.

        :v2 API:
        """
        self.vault_manager.get_vault(g.usr_did)

        def get_out_file_info(metadata):
            return {
                'name': metadata[COL_IPFS_FILES_PATH],
                'is_file': metadata[COL_IPFS_FILES_IS_FILE],
                'size': metadata[SIZE],
                'is_encrypt': metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False),
                'encrypt_method': metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''),
            }

        docs = self.list_folder_with_path(g.usr_did, g.app_did, path)
        return {
            'value': list(map(lambda d: get_out_file_info(d), docs))
        }

    def list_folder_with_path(self, user_did, app_did, folder_path):
        """ list files by folder with path, empty string means root path

        'public' for v1
        """

        return self.file_manager.get_all_metadatas(user_did, app_did, folder_path)

    def get_properties(self, path):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        metadata = self.get_file_metadata(g.usr_did, g.app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'is_file': metadata[COL_IPFS_FILES_IS_FILE],
            'size': int(metadata[SIZE]),
            'is_encrypt': metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False),
            'encrypt_method': metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''),
            'created': int(metadata['created']),
            'updated': int(metadata['modified']),
        }

    def get_hash(self, path):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)

        metadata = self.get_file_metadata(g.usr_did, g.app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'algorithm': 'SHA256',
            'hash': metadata[COL_IPFS_FILES_SHA256]
        }

    def upload_file_with_path(self, user_did, app_did, file_path: str, is_encrypt=False, encrypt_method=''):
        """ The routine to process the file uploading:
            1. Receive the content of uploaded file and cache it a temp file;
            2. Add this file onto IPFS node and return with CID;
            3. Create a new metadata with the CID and store them as document;
            4. Cached the temp file to specific cache directory.

        'public' for v1, scripting service

        :param user_did: the user did
        :param app_did: the application did
        :param file_path: the file relative path, not None
        :param is_encrypt
        :param encrypt_method
        :return: None
        """
        # upload to the temporary file and then to IPFS node.
        temp_file = LocalFile.generate_tmp_file_path()
        LocalFile.write_file_by_request_stream(temp_file)
        return self.upload_file_from_local(user_did, app_did, file_path, temp_file, is_encrypt, encrypt_method)

    def upload_file_from_local(self, user_did, app_did, file_path: str, local_path: Path, is_encrypt=False, encrypt_method='', only_import=False):
        """ Upload file to ipfs node from local file.
        1. 'only_import' and 'kwargs' is only for v1 relating script.

        The process routine:
        1. upload file to ipfs node.
        2. insert/update file metadata for the user.
        3. cache the file to the cache dir of the user's vault.
        4. cache the file to global cache folder if public

        'public' for upgrading files service from v1 to v2 (local -> ipfs)

        :param user_did: user did
        :param app_did: application did
        :param file_path: file path
        :param local_path: the uploading based file.
        :param only_import: Just import the file to ipfs node, keep the local file and not increase the file storage usage size.
        :param is_encrypt
        :param encrypt_method
        :return None
        """
        # upload the file to ipfs node.
        new_cid, increased_size = self.ipfs_client.upload_file(local_path), 0

        # insert or update file metadata.
        old_metadata = self.get_file_metadata(user_did, app_did, file_path, throw_exception=False)

        # add new or update exist one
        sha256, size = LocalFile.get_sha256(local_path.as_posix()), local_path.stat().st_size
        new_metadata = self.file_manager.add_metadata(user_did, app_did, file_path, sha256, size, new_cid, is_encrypt, encrypt_method)
        if not old_metadata:
            IpfsCidRef(new_cid).increase()
            increased_size = size
        elif old_metadata[COL_IPFS_FILES_IPFS_CID] != new_cid:
            IpfsCidRef(new_cid).increase()
            IpfsCidRef(old_metadata[COL_IPFS_FILES_IPFS_CID]).decrease()
            increased_size = new_metadata[SIZE] - old_metadata[SIZE]

        if increased_size and not only_import:
            self.vault_manager.update_user_files_size(user_did, increased_size)

        # cache the uploaded file.
        cache_file = LocalFile.get_cid_cache_dir(user_did, need_create=True) / new_cid
        if not cache_file.exists():
            if only_import:
                shutil.copy(local_path.as_posix(), cache_file.as_posix())
            else:
                shutil.move(local_path.as_posix(), cache_file.as_posix())

        return new_cid

    def delete_file_metadata(self, user_did, app_did, rel_path, cid):
        """ 'public' for upgrading files service from v1 to v2 (local -> ipfs) """
        self.file_manager.delete_metadata(user_did, app_did, rel_path, cid)
        logging.info(f'[ipfs-files] Remove an existing file {rel_path}')

    def download_file_with_path(self, user_did, app_did, path: str):
        """ Download the target file with the following steps:
            1. Check target file already be cached, then just use this file, otherwise:
            2. Download file from IPFS to cache directory;
            3. Response to requrester with this cached file.

        'public' for v1, scripting service

        :param user_did: The user did.
        :param app_did: The application did
        :param path:
        :return:
        """
        metadata = self.get_file_metadata(user_did, app_did, path)
        cached_file = LocalFile.get_cid_cache_dir(user_did) / metadata[COL_IPFS_FILES_IPFS_CID]
        if not cached_file.exists():
            self.ipfs_client.download_file(metadata[COL_IPFS_FILES_IPFS_CID], cached_file)
        return LocalFile.get_download_response(cached_file)

    def move_copy_file(self, user_did, app_did, src_path: str, dst_path: str, is_copy=False):
        """ Move/Copy file with the following steps:
            1. Check source file existing and file with destination name existing. If not, then
            2. Move or copy file;
            3. Update metadata

        'public' for v1

        :param user_did:
        :param app_did:
        :param src_path: The path of the source file.
        :param dst_path: The path of the destination file.
        :param is_copy: True means copy file, else move.
        :return: Json data of the response.
        """

        # check two file paths
        src_metadata = self.file_manager.get_metadata(user_did, app_did, src_path)
        try:
            dst_metadata = self.file_manager.get_metadata(user_did, app_did, dst_path)
            raise AlreadyExistsException(f'The destination file {dst_path} already exists, impossible to {"copy" if is_copy else "move"}.')
        except FileNotFoundException:
            pass

        # do copy or move
        if is_copy:
            self.file_manager.add_metadata(user_did, app_did, dst_path,
                                           src_metadata[COL_IPFS_FILES_SHA256], src_metadata[SIZE], src_metadata[COL_IPFS_FILES_IPFS_CID],
                                           src_metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False), src_metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''))
            IpfsCidRef(src_metadata[COL_IPFS_FILES_IPFS_CID]).increase()
            self.vault_manager.update_user_files_size(user_did, src_metadata[SIZE])
        else:
            self.file_manager.move_metadata(user_did, app_did, src_path, dst_path)

        return {
            'name': dst_path
        }

    def get_file_metadata(self, user_did, app_did, path: str, throw_exception=True):
        """ 'public' for v1, scripting service """
        try:
            return self.file_manager.get_metadata(user_did, app_did, path)
        except FileNotFoundException as e:
            if throw_exception:
                raise e
            else:
                return None
