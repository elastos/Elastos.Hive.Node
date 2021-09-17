import hashlib
import os
from datetime import datetime

from pathlib import Path

from src.utils_v1.common import did_tail_part, create_full_path_dir

from src.settings import hive_setting
from src.utils_v1.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, NOT_FOUND, SUCCESS, FORBIDDEN
from src.utils_v1.flask_rangerequest import RangeRequest


def get_vault_path(did):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def get_save_files_path(did, app_id):
    """ get files root path """
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / app_id / "files"
    else:
        path = path.resolve() / did_tail_part(did) / app_id / "files"
    return path.resolve()


def filter_path_root(name):
    return name[1:] if len(name) > 0 and name[0] == "/" else name


def query_upload_get_filepath(did, app_id, file_name):
    """
    Create the parent folder of the file and return the full path of the file.
    Return: full file path, error message
    """
    err = {}

    path = get_save_files_path(did, app_id)
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


def query_download(did, app_id, file_name):
    if file_name is None:
        return None, BAD_REQUEST
    filename = filter_path_root(file_name)

    path = get_save_files_path(did, app_id)
    file_full_name = (path / filename).resolve()

    if not file_full_name.exists():
        return None, NOT_FOUND

    if not file_full_name.is_file():
        return None, FORBIDDEN

    size = file_full_name.stat().st_size
    with open(file_full_name, 'rb') as f:
        etag = RangeRequest.make_etag(f)
    last_modified = datetime.utcnow()

    return RangeRequest(open(file_full_name, 'rb'),
                        etag=etag,
                        last_modified=last_modified,
                        size=size).make_response(), SUCCESS


def query_properties(did, app_id, name):
    """
    Return: file property information of relative file name.
    """
    data, err = {}, {}

    name = filter_path_root(name)
    path = get_save_files_path(did, app_id)
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


def query_hash(did, app_id, name):
    data, err = {}, {}

    name = filter_path_root(name)
    path = get_save_files_path(did, app_id)
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
