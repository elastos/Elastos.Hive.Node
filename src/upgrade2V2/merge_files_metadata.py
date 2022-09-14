# -*- coding: utf-8 -*-

"""
Upload the files metadata to v2 node.
1. Consider try this script again.
"""
import json
import logging
import sys
from pathlib import Path

from src.modules.files.file_metadata import FileMetadataManager
from src.modules.files.files_service import IpfsFiles
from src.upgrade2V2.gen_files_metadata import get_vaults_root, get_files_metadata_file, generate_app_files_root
from src.utils.consts import COL_IPFS_FILES_PATH, COL_IPFS_FILES_SHA256, SIZE, COL_IPFS_FILES_IPFS_CID


def init_app_files_metadata(vaults_root, user_did, app_did, files: list):
    logging.info(f'enter init file metadata for {user_did}, {app_did}.')
    if not files:
        logging.info(f'leave init file metadata for {user_did}, {app_did}, no files.')
        return
    files_root = generate_app_files_root(vaults_root, user_did, app_did)
    ipfs_files = IpfsFiles()
    for file in files:
        ipfs_files.upload_file_from_local(user_did, app_did, file['path'], files_root / file['path'],
                                          only_import=True, created=file['created'], modified=file['modified'])
    logging.info(f'leave init file metadata for {user_did}, {app_did}.')


def get_file_by_path(files: list, path):
    result = list(filter(lambda f: f['path'] == path, files))
    return result[0] if result else None


def is_need_insert_or_update(cur_file, dst_file):
    if not cur_file:
        return True
    if dst_file['modified'] < cur_file['modified']:
        return False
    if cur_file['sha256'] == dst_file['sha256'] and cur_file['size'] == dst_file['size']:
        return False
    return True


def calculate_changed_files(cur_files, dst_files):
    update_files, delete_files = [], []
    for file in dst_files:
        cur_file = get_file_by_path(cur_files, file['path'])
        if is_need_insert_or_update(cur_file, file):
            update_files.append(file)
    # Do not handle files which will be removed because these maybe update on v2 side.
    # for file in cur_files:
    #     dst_file = get_file_by_path(dst_files, file['path'])
    #     if not dst_file:
    #         delete_files.append(file)
    return update_files, delete_files


def update_app_files_metadata(vaults_root, user_did, app_did, files: list):
    logging.info(f'enter update file metadata for {user_did}, {app_did}.')

    cur_files = FileMetadataManager().get_all_metadatas(user_did, app_did)
    if not cur_files:
        return

    cur_files = list(map(lambda doc: {
                "path": doc[COL_IPFS_FILES_PATH],
                "sha256": doc[COL_IPFS_FILES_SHA256],
                "size": doc[SIZE],
                "cid": doc[COL_IPFS_FILES_IPFS_CID],
                "created": doc['created'],
                "modified": doc['modified']
            }, cur_files))

    ipfs_files, files_root = IpfsFiles(), generate_app_files_root(vaults_root, user_did, app_did)
    update_files, delete_files = calculate_changed_files(cur_files, files)
    for file in update_files:
        ipfs_files.upload_file_from_local(user_did, app_did, file['path'], files_root / file['path'],
                                          only_import=True, created=file['created'], modified=file['modified'])
    for file in delete_files:
        ipfs_files.delete_file_metadata(user_did, app_did, file['path'], file['cid'])

    logging.info(f'leave update file metadata for {user_did}, {app_did}.')


def upload_user_files_metadata(vaults_root, user_did, user_file_metadata, only_import):
    for k, v in user_file_metadata.items():
        if only_import:
            init_app_files_metadata(vaults_root, user_did, k, v)
        else:
            update_app_files_metadata(vaults_root, user_did, k, v)


def upload_files_metadata(vaults_root, files_metadata, only_import):
    """ for init """
    for k, v in files_metadata.items():
        upload_user_files_metadata(vaults_root, k, v, only_import)


def main():
    if len(sys.argv) != 3:
        print(f'Usage: python {sys.argv[0]} [init:update] <HIVE_DATA>')
        return

    action, data_root = sys.argv[1], Path(sys.argv[2])
    if action not in ['init', 'update']:
        print(f'Invalid action: {action}')
        return
    if not data_root.exists() or not get_vaults_root(data_root).exists() \
            or not get_files_metadata_file(data_root).exists():
        print(f'Invalid data root: {data_root.as_posix()}')
        return

    logging.info(f'start with action: {action}')

    with get_files_metadata_file(data_root).open('r') as f:
        files_metadata = json.load(f)

    upload_files_metadata(get_vaults_root(data_root), files_metadata, action == 'init')

    logging.info('all things done!')


if __name__ == '__main__':
    main()
