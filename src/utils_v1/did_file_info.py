import os
import hashlib
from pathlib import Path

from src.settings import hive_setting
from src.utils_v1.common import did_tail_part, create_full_path_dir
from src.utils_v1.error_code import INTERNAL_SERVER_ERROR, NOT_FOUND


def get_vault_path(did):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def get_save_files_path(did, app_did):
    """ get files root path """
    return get_user_did_path(did) / app_did / 'files'


def get_user_did_path(did):
    """ get the path of the user did """
    path = Path(hive_setting.VAULTS_BASE_DIR)
    return (path / did_tail_part(did)) if path.is_absolute() else (path.resolve() / did_tail_part(did))


def filter_path_root(name):
    return name[1:] if len(name) > 0 and name[0] == "/" else name


def query_upload_get_filepath(did, app_did, file_name):
    """
    Create the parent folder of the file and return the full path of the file.
    Return: full file path, error message
    """
    err = {}

    path = get_save_files_path(did, app_did)
    full_path_name = (path / file_name).resolve()

    if not create_full_path_dir(full_path_name.parent):
        err["status_code"], err["description"] = INTERNAL_SERVER_ERROR, "make path dir error"
        return full_path_name, err

    if not full_path_name.exists():
        full_path_name.touch(exist_ok=True)

    if full_path_name.is_dir():
        err["status_code"], err["description"] = NOT_FOUND, "file name is a directory"
        return full_path_name, err

    return full_path_name, err


def query_properties(did, app_did, name):
    """
    Return: file property information of relative file name.
    """
    data, err = {}, {}

    name = filter_path_root(name)
    path = get_save_files_path(did, app_did)
    full_path_name = (path / name).resolve()

    if not full_path_name.exists():
        err["status_code"], err["description"] = NOT_FOUND, "file not exists"
        return data, err

    stat_info = full_path_name.stat()

    data = {
        "type": "file" if full_path_name.is_file() else "folder",
        "name": name,
        "size": stat_info.st_size,
        "last_modify": stat_info.st_mtime,
    }
    return data, err


def query_hash(did, app_did, name):
    data, err = {}, {}

    name = filter_path_root(name)
    path = get_save_files_path(did, app_did)
    full_path_name = (path / name).resolve()

    if not full_path_name.exists() or (not full_path_name.is_file()):
        err["status_code"], err["description"] = NOT_FOUND, "file not exists"
        return data, err

    # INFO: to get sha256 by full path, use fm.get_file_content_sha256()
    buf_size = 65536  # lets read stuff in 64kb chunks!
    sha = hashlib.sha256()
    with full_path_name.open('rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha.update(data)
    data = {"SHA256": sha.hexdigest()}
    return data, err


def get_dir_size(input_path: str, total_size):
    return get_directory_size(input_path)


def get_directory_size(directory: str):
    """Returns the `directory` size in bytes."""
    total = 0
    try:
        # print("[+] Getting the size of", directory)
        for entry in os.scandir(directory):
            if entry.is_file():
                # if it's a file, use stat() function
                total += entry.stat().st_size
            elif entry.is_dir():
                # if it's a directory, recursively call this function
                total += get_directory_size(entry.path)
    except NotADirectoryError:
        # if `directory` isn't a directory, get the file size then
        return os.path.getsize(directory)
    except PermissionError:
        # if for whatever reason we can't open the folder, return 0
        return 0
    return total
