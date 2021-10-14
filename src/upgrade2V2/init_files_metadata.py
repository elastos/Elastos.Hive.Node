# -*- coding: utf-8 -*-

"""
Upload the files metadata to v2 node.
1. Consider try this script again.
"""
import json
import sys
from pathlib import Path

from src.modules.ipfs.ipfs_files import IpfsFiles
from src.upgrade2V2.gen_files_metadata import get_vaults_root, get_files_metadata_file, generate_app_files_root


def upload_app_files_metadata(vaults_root, user_did, app_did, files: list):
    files_root = generate_app_files_root(vaults_root, user_did, app_did)
    ipfs_files = IpfsFiles()
    for file in files:
        ipfs_files.upload_file_from_local(user_did, app_did, file['path'], files_root / file['path'],
                                          is_only_import=True)


def upload_user_files_metadata(vaults_root, user_did, user_file_metadata):
    for k, v in user_file_metadata.items():
        upload_app_files_metadata(vaults_root, user_did, k, v)


def upload_files_metadata(vaults_root, files_metadata):
    for k, v in files_metadata.items():
        upload_user_files_metadata(vaults_root, k, v)


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <HIVE_DATA>')
        return

    data_root = Path(sys.argv[1])
    if not data_root.exists() or not get_vaults_root(data_root).exists() \
            or not get_files_metadata_file(data_root).exists():
        print(f'Invalid data root: {data_root.as_posix()}')
        return

    with get_files_metadata_file(data_root).open('r') as f:
        files_metadata = json.load(f)

    upload_files_metadata(get_vaults_root(data_root), files_metadata)


if __name__ == '__main__':
    main()
