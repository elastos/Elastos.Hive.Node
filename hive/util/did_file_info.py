import logging
from datetime import datetime

from bson import ObjectId
from flask import request
from pymongo import MongoClient

from pathlib import Path
from hive.util.common import did_tail_part, create_full_path_dir

from hive.util.constants import DID_INFO_DB_NAME, FILE_INFO_COL, FILE_INFO_BELONG_DID, FILE_INFO_BELONG_APP_ID, \
    FILE_INFO_FILE_NAME, FILE_INFO_FILE_SIZE, FILE_INFO_FILE_CREATE_TIME, FILE_INFO_FILE_MODIFY_TIME
from hive.settings import MONGO_HOST, MONGO_PORT, VAULTS_BASE_DIR
from hive.util.flask_rangerequest import RangeRequest


def get_save_files_path(did, app_id):
    path = Path(VAULTS_BASE_DIR)
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


def query_upload(did, app_id, file_name):
    err = (None, None)

    path = get_save_files_path(did, app_id)
    full_path_name = (path / file_name).resolve()

    if not create_full_path_dir(full_path_name.parent):
        err[0], err[1] = 500, "make path dir error"
        return err

    if not full_path_name.exists():
        full_path_name.touch(exist_ok=True)

    if full_path_name.is_dir():
        err[0], err[1] = 404, "file name is a directory"
        return err
    try:
        with open(full_path_name, "bw") as f:
            chunk_size = 4096
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
                f.write(chunk)
        return None
    except Exception as e:
        err[0], err[1] = 500, f"Exception: method: 'query_upload', Err: {str(e)}"
        return err


def query_download(did, app_id, file_name):
    if file_name is None:
        return None, 400
    filename = filter_path_root(file_name)

    path = get_save_files_path(did, app_id)
    file_full_name = (path / filename).resolve()

    if not file_full_name.exists():
        return None, 404

    if not file_full_name.is_file():
        return None, 403

    size = file_full_name.stat().st_size
    with open(file_full_name, 'rb') as f:
        etag = RangeRequest.make_etag(f)
    last_modified = datetime.utcnow()

    return RangeRequest(open(file_full_name, 'rb'),
                        etag=etag,
                        last_modified=last_modified,
                        size=size).make_response(), 200


def add_file_info(did, app_id, name, info_dic):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]

    base_dic = {FILE_INFO_BELONG_DID: did,
                FILE_INFO_BELONG_APP_ID: app_id,
                FILE_INFO_FILE_NAME: name,
                FILE_INFO_FILE_CREATE_TIME: datetime.now().timestamp(),
                FILE_INFO_FILE_MODIFY_TIME: datetime.now().timestamp()
                }

    did_dic = dict(base_dic, **info_dic)
    i = col.insert_one(did_dic)
    return i


def update_file_size(did, app_id, name, size):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    value = {"$set": {FILE_INFO_FILE_SIZE: size, FILE_INFO_FILE_MODIFY_TIME: datetime.now().timestamp()}}
    ret = col.update_one(query, value)
    return ret


def update_file_info(did, app_id, name, info_dic):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    info_dic[FILE_INFO_FILE_MODIFY_TIME] = datetime.now().timestamp()
    value = {"$set": info_dic}
    ret = col.update_one(query, value)
    return ret


def remove_file_info(did, app_id, name):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    ret = col.delete_one(query)
    return ret


def get_file_info(did, app_id, name):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    info = col.find_one(query)
    return info


def get_file_info_by_id(file_id):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {"_id": ObjectId(file_id)}
    info = col.find_one(query)
    return info
