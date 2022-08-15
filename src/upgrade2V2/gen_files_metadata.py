# -*- coding: utf-8 -*-

"""
Generate the file metadata of the vaults. The metadata format is like this:
{
    "<user_did>": {
        "<app_did>": [{
            "path": <relative_path>,
            "sha256": <str>,
            "size": <int>,
            "created": <timestamp, float>,
            "modified": <timestamp, float>
        }]
    }
}
"""
import json
import logging
import sys
from pathlib import Path

from src.modules.files.local_file import LocalFile


skip_file_names = ['.DS_Store', ]


def get_vaults_root(data_root: Path):
    return data_root / 'vaults'


def get_files_metadata_file(data_root: Path):
    return data_root / 'vaults.metadata.json'


def get_app_files_root(app_root: Path):
    return app_root / 'files'


def generate_app_files_root(vaults_root: Path, user_did, app_did):
    return get_app_files_root(vaults_root / str.split(user_did, ':')[2] / app_did)


def get_file_info(relative_dir_name, file: Path):
    return {
        'path': f'{relative_dir_name}/{file.name}' if relative_dir_name else file.name,
        'sha256': LocalFile.get_sha256(file.as_posix()),
        'size': file.stat().st_size,
        'created': LocalFile.get_file_ctime(file.as_posix()),
        'modified': file.stat().st_mtime
    }


def get_all_app_files(files_root: Path, relative_dir_name, result):
    folder_path = Path(f'{files_root.as_posix()}/{relative_dir_name}')
    for file in folder_path.iterdir():
        if file.is_dir():
            name = file.name if not relative_dir_name else f'{relative_dir_name}/{file.name}'
            get_all_app_files(files_root, name, result)
        elif file.name not in skip_file_names:
            result.append(get_file_info(relative_dir_name, file))


def generate_app_files(app_root: Path):
    result = []
    if get_app_files_root(app_root).exists():
        get_all_app_files(get_app_files_root(app_root), '', result)
    return result


def generate_vault(vault_root: Path):
    result = {}
    for file in vault_root.iterdir():
        if file.is_dir():
            app_did = file.name
            result[app_did] = generate_app_files(file)
    return result


def generate_vaults(data_root: Path):
    result = {}
    for file in get_vaults_root(data_root).iterdir():
        if file.is_dir():
            user_did = f'did:elastos:{file.name}'
            result[user_did] = generate_vault(file)
    return result


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <HIVE_DATA>')
        return

    data_root = Path(sys.argv[1])
    if not data_root.exists() or not get_vaults_root(data_root).exists():
        print(f'Invalid data root: {data_root.as_posix()}')
        return

    files_metadata = generate_vaults(data_root)
    with get_files_metadata_file(data_root).open('w') as f:
        json.dump(files_metadata, f)

    logging.info('all things done!')


if __name__ == '__main__':
    main()
