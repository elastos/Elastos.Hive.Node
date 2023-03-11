# -*- coding: utf-8 -*-

"""
The entrance for ipfs module.
"""
import logging
import shutil
from pathlib import Path

from flask import g

from src.modules.database.mongodb_client import mcli
from src.modules.files.file_cache import FileCache
from src.utils.consts import COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, COL_IPFS_FILES_IS_FILE, COL_IPFS_FILES_SIZE, COL_IPFS_FILES_IPFS_CID, \
    COL_IPFS_FILES_IS_ENCRYPT, COL_IPFS_FILES_ENCRYPT_METHOD, COL_COMMON_CREATED, COL_COMMON_MODIFIED
from src.utils.http_exception import FileNotFoundException, AlreadyExistsException
from src.modules.subscription.vault import VaultManager
from src.modules.files.collection_file_metadata import CollectionFileMetadata
from src.modules.files.ipfs_client import IpfsClient
from src.modules.files.local_file import LocalFile
from src.modules.files.collection_ipfs_cid_ref import CollectionIpfsCidRef
from src.modules.files.collection_anonymous_files import CollectionAnonymousFiles


class FilesService:
    def __init__(self):
        """ IPFS node is being used to store immutable block data (files):
        1. Each user_did/app_did has the sandboxing to cache application data;
        2. Each user_did/app_did has the mongodb collection to manage the metadata on the block data on IPFS node;
        3. Once a block data (usually file) has been uploaded to hive node, it would be cached on local filesystem
        first, afterwards it also would be uploaded and pined to the paired IPFS node.
        4. The CID to the block data on IPFS would be managed as the field of metadata in the collection.

        """
        self.vault_manager = VaultManager()
        self.ipfs_client = IpfsClient()

    def upload_file(self, path, is_public: bool, is_encrypt: bool, encrypt_method: str):
        """ Upload file to the backend IPFS node and keeps metadata on the node.

        :param path: The file path
        :param is_public: Whether the file need be shared by any others.
        :param is_encrypt: Whether the file is encrypted.
        :param encrypt_method: Encrypt method when is_encrypt is True.
        :return: File path and the cid of IPFS node.
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        cid = self.v1_upload_file(g.usr_did, g.app_did, path, is_encrypt, encrypt_method)

        if is_public:
            mcli.get_col(CollectionAnonymousFiles).save_anonymous_file(path, cid)
        else:
            mcli.get_col(CollectionAnonymousFiles).delete_anonymous_file(path)

        return {
            'name': path,
            'cid': cid if is_public else ''
        }

    def download_file(self, path):
        """ Download file content from the backend IPFS node.

        :param path: The file path
        :return: The content of the file.
        """

        self.vault_manager.get_vault(g.usr_did)

        return self.v1_download_file(g.usr_did, g.app_did, path)

    def delete_file(self, path):
        """ Delete a file from the vault.
        1. Remove the cached file in local filesystem;
        2. Unpin the file data from corresponding IPFS node.

        :param path: The file path
        :return: None
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        mcli.get_col(CollectionAnonymousFiles).delete_anonymous_file(path)
        self.v1_delete_file(g.usr_did, g.app_did, path, check_exists=True)

    def move_file(self, src_path, dst_path):
        """ Move file from one place to the other place.

        :param src_path: The source file path.
        :param dst_path: The destination file path.
        :return: The destination file path.
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        mcli.get_col(CollectionAnonymousFiles).delete_anonymous_file(src_path)
        return self.v1_move_copy_file(g.usr_did, g.app_did, src_path, dst_path)

    def copy_file(self, src_path, dst_path):
        """ Copy file from one place to the other place.

        :param src_path: The source file path.
        :param dst_path: The destination file path.
        :return: The destination file path.
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        return self.v1_move_copy_file(g.usr_did, g.app_did, src_path, dst_path, is_copy=True)

    def list_folder(self, path):
        """ List the files (includes sub-folders) under the specific directory.

        :param path: The folder path. Empty means root folder.
        :return: Files list.
        """
        self.vault_manager.get_vault(g.usr_did)

        def get_out_file_info(metadata):
            return {
                'name': metadata[COL_IPFS_FILES_PATH],
                'is_file': metadata[COL_IPFS_FILES_IS_FILE],
                'size': metadata[COL_IPFS_FILES_SIZE],
                'is_encrypt': metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False),
                'encrypt_method': metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''),
            }

        docs = self.v1_list_folder(g.usr_did, g.app_did, path)
        return {
            'value': list(map(lambda d: get_out_file_info(d), docs))
        }

    def get_properties(self, path):
        """ Get the properties of the file which comes from the file metadata.

        :param path: The file path.
        :return: The properties of the file.
        """

        self.vault_manager.get_vault(g.usr_did)

        metadata = self.v1_get_file_metadata(g.usr_did, g.app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'is_file': metadata[COL_IPFS_FILES_IS_FILE],
            'size': int(metadata[COL_IPFS_FILES_SIZE]),
            'is_encrypt': metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False),
            'encrypt_method': metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''),
            'created': int(metadata[COL_COMMON_CREATED]),
            'updated': int(metadata[COL_COMMON_MODIFIED]),
        }

    def get_hash(self, path):
        """ Get the hash of the file content.

        :param path: The file path.
        :return: The hash information of the file content.
        """

        self.vault_manager.get_vault(g.usr_did)

        metadata = self.v1_get_file_metadata(g.usr_did, g.app_did, path)
        return {
            'name': metadata[COL_IPFS_FILES_PATH],
            'algorithm': 'SHA256',
            'hash': metadata[COL_IPFS_FILES_SHA256]
        }

    def v1_upload_file(self, user_did, app_did, file_path: str, is_encrypt=False, encrypt_method=''):
        """ The routine to process the file uploading:
        1. Receive the content of uploaded file and cache it a temp file;
        2. Add this file onto IPFS node and return with CID;
        3. Create a new metadata with the CID and store them as document;
        4. Cached the temp file to specific cache directory.

        :param user_did: The user did
        :param app_did: The application did
        :param file_path: The file relative path, not None.
        :param is_encrypt: Whether the file content is encrypted.
        :param encrypt_method The encryption method if is_encrypt is True.
        :return: The cid of the file.
        """

        # upload to the temporary file and then to IPFS node.
        temp_file = LocalFile.generate_tmp_file_path()
        LocalFile.write_file_by_request_stream(temp_file)
        return self.tov2_upload_file_from_local(user_did, app_did, file_path, temp_file, is_encrypt, encrypt_method)

    def v1_download_file(self, user_did, app_did, path: str):
        """ Download the target file with the following steps:
        1. Check target file already be cached, then just use this file, otherwise:
        2. Download file from IPFS to cache directory.
        3. Response to requester with this cached file.

        :param user_did: The user did.
        :param app_did: The application did.
        :param path: The file path.
        :return: The response with the file content.
        """

        metadata = self.v1_get_file_metadata(user_did, app_did, path)
        cached_file = FileCache.get_path(user_did, metadata)
        if not cached_file.exists():
            self.ipfs_client.download_file(metadata[COL_IPFS_FILES_IPFS_CID], cached_file)
        return LocalFile.get_download_response(cached_file)

    def v1_delete_file(self, user_did, app_did, path, check_exists=False):
        """ Only do the file deletion.

        :param user_did: The user did.
        :param app_did: The application did.
        :param path: The file path.
        :param check_exists: If True and file not exists, raise FileNotFoundException.
        :return: None
        """

        col = mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did)
        try:
            metadata = col.get_file_metadata(path)
        except FileNotFoundException as e:
            if check_exists:
                raise e
            else:
                return

        # do real remove
        LocalFile.remove_ipfs_cache_file(user_did, metadata[COL_IPFS_FILES_IPFS_CID])
        col.delete_file_metadata(path, metadata[COL_IPFS_FILES_IPFS_CID])
        self.vault_manager.update_user_files_size(user_did, 0 - metadata[COL_IPFS_FILES_SIZE])

    def v1_list_folder(self, user_did, app_did, folder_path):
        """ List files by the folder path, empty string means root path.

        :param user_did: The user did.
        :param app_did: The application did.
        :param folder_path: The path of the folder.
        :return: The files list.
        """

        return mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).get_all_file_metadatas(folder_path)

    def v1_move_copy_file(self, user_did, app_did, src_path: str, dst_path: str, is_copy=False):
        """ Move/Copy file with the following steps:
        1. Check source file existing and file with destination name existing. If not, then
        2. Move or copy file;
        3. Update metadata

        :param user_did: The user did.
        :param app_did: The application did.
        :param src_path: The path of the source file.
        :param dst_path: The path of the destination file.
        :param is_copy: True means copy file, else move.
        :return: The destination path.
        """
        col = mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did)

        # check two file paths
        src_metadata = col.get_file_metadata(src_path)
        try:
            dst_metadata = col.get_file_metadata(dst_path)
            raise AlreadyExistsException(f'The destination file {dst_path} already exists, impossible to {"copy" if is_copy else "move"}.')
        except FileNotFoundException:
            pass

        # do copy or move
        if is_copy:
            col.upsert_file_metadata(dst_path,
                                     src_metadata[COL_IPFS_FILES_SHA256], src_metadata[COL_IPFS_FILES_SIZE], src_metadata[COL_IPFS_FILES_IPFS_CID],
                                     src_metadata.get(COL_IPFS_FILES_IS_ENCRYPT, False), src_metadata.get(COL_IPFS_FILES_ENCRYPT_METHOD, ''))
            mcli.get_col(CollectionIpfsCidRef).increase_cid_ref(src_metadata[COL_IPFS_FILES_IPFS_CID])
            self.vault_manager.update_user_files_size(user_did, src_metadata[COL_IPFS_FILES_SIZE])
        else:
            col.move_file_metadata(src_path, dst_path)

        return {
            'name': dst_path
        }

    def v1_get_file_metadata(self, user_did, app_did, path: str, check_exists=True):
        """ Get the file metadata.

        :param user_did: The user did.
        :param app_did: The user did.
        :param path: The file path.
        :param check_exists: True means throwing FileNotFoundException when file does not exist.
        :return: The metadata of the file.
        """

        try:
            return mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).get_file_metadata(path)
        except FileNotFoundException as e:
            if check_exists:
                raise e
            else:
                return None

    def tov2_upload_file_from_local(self, user_did, app_did, file_path: str, local_path: Path, is_encrypt=False, encrypt_method='', only_import=False):
        """ Upload file to IPFS node from local file.
        1. 'only_import' is only for tov2 upgrading script.

        The process routine:
        1. upload file to ipfs node.
        2. insert/update file metadata for the user.
        3. cache the file to the cache dir of the user's vault.
        4. cache the file to global cache folder if public

        :param user_did: The user did.
        :param app_did: The application did.
        :param file_path: The file path.
        :param local_path: The local file path.
        :param only_import: Just import the file to IPFS node,
                            keep the local file and not increase the file storage usage size. (tov2 upgrading script)
        :param is_encrypt: Whether the file content is encrypted.
        :param encrypt_method: The encryption method when is_encrypt is True.
        :return: CID of the file.
        """

        # upload the file to ipfs node.
        new_cid, increased_size = self.ipfs_client.upload_file(local_path), 0

        # insert or update file metadata.
        old_metadata = self.v1_get_file_metadata(user_did, app_did, file_path, check_exists=False)

        # add new or update exist one
        sha256, size = LocalFile.get_sha256(local_path.as_posix()), local_path.stat().st_size
        new_metadata = mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).upsert_file_metadata(file_path, sha256, size, new_cid, is_encrypt, encrypt_method)
        if not old_metadata:
            mcli.get_col(CollectionIpfsCidRef).increase_cid_ref(new_cid)
            increased_size = size
        elif old_metadata[COL_IPFS_FILES_IPFS_CID] != new_cid:
            mcli.get_col(CollectionIpfsCidRef).increase_cid_ref(new_cid)
            already_removed = mcli.get_col(CollectionIpfsCidRef).decrease_cid_ref(old_metadata[COL_IPFS_FILES_IPFS_CID])
            if already_removed:
                FileCache.remove_file(user_did, old_metadata[COL_IPFS_FILES_IPFS_CID])
            increased_size = new_metadata[COL_IPFS_FILES_SIZE] - old_metadata[COL_IPFS_FILES_SIZE]

        if increased_size and not only_import:
            self.vault_manager.update_user_files_size(user_did, increased_size)

        # cache the uploaded file.
        cache_file = FileCache.get_path_by_cid(user_did, new_cid)
        if not cache_file.exists():
            if only_import:
                shutil.copy(local_path.as_posix(), cache_file.as_posix())
            else:
                shutil.move(local_path.as_posix(), cache_file.as_posix())

        return new_cid

    def tov2_delete_file_metadata(self, user_did, app_did, path, cid):
        """ Only for tov2 upgrading script. Delete the metadata of the file.

        :param user_did: The user did.
        :param app_did: The application did.
        :param path: The path of the file.
        :param cid: The CID of the file.
        :return: None
        """

        mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).delete_file_metadata(path, cid)
        logging.info(f'[ipfs-files] Remove an existing file {path}')
