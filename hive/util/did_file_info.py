import hashlib
import logging
import os
from datetime import datetime

from pathlib import Path

from hive.util.common import did_tail_part, create_full_path_dir

from hive.settings import hive_setting
from hive.util.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, NOT_FOUND, SUCCESS, FORBIDDEN
from hive.util.flask_rangerequest import RangeRequest


def get_vault_path(did):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def get_save_files_path(did, app_id):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / app_id / "files"
    else:
        path = path.resolve() / did_tail_part(did) / app_id / "files"
    return path.resolve()


def filter_path_root(name):
    if name[0] == "/":
        return name[1:]
    else:
        return name


def query_upload_get_filepath(did, app_id, file_name):
    """
    Return: full file path
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


def get_dir_size(input_path, total_size):
    path = Path(input_path)
    path.resolve()
    if not path.exists():
        return 0.0

    file_list = os.listdir(path.as_posix())
    for i in file_list:
        i_path = os.path.join(path, i)
        if os.path.isdir(i_path):
            try:
                total_size += get_dir_size(i_path, total_size)
            except RecursionError:
                logging.getLogger("Hive_file_info").error("Err: get_dir_size too much for get_file_size")
        else:
            total_size += os.path.getsize(i_path)

    return total_size



