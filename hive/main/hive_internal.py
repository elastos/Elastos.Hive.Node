import pickle
import shutil
from pathlib import Path
from flask import request, Response

from hive.util.auth import did_auth
from hive.util.common import deal_dir, get_file_md5_info, gene_temp_file_name, get_file_checksum_list, \
    create_full_path_dir
from hive.util.constants import HIVE_MODE_DEV, BACKUP_ACCESS, CHUNK_SIZE, VAULT_BACKUP_SERVICE_USE_STORAGE
from hive.util.did_file_info import filter_path_root, get_dir_size
from hive.util.error_code import BAD_REQUEST, UNAUTHORIZED, SUCCESS, NOT_FOUND, CHECKSUM_FAILED, \
    SERVER_MKDIR_ERROR, FORBIDDEN, SERVER_SAVE_FILE_ERROR, SERVER_PATCH_FILE_ERROR, SERVER_MOVE_FILE_ERROR
from hive.util.flask_rangerequest import RangeRequest
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, get_vault_backup_path, \
    update_vault_backup_service_item
from hive.util.payment.vault_service_manage import can_access_backup
from hive.util.pyrsync import patchstream, gene_blockchecksums
from hive.util.vault_backup_info import *
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, did_post_json_param_pre_proc, pre_proc

import logging

logger = logging.getLogger("HiveInternal")


class HiveInternal:
    mode = HIVE_MODE_DEV

    def __init__(self):
        self.app = None
        self.response = ServerResponse("HiveInternal")
        self.backup_ftp = None

    def init_app(self, app, mode):
        backup_path = Path(hive_setting.BACKUP_VAULTS_BASE_DIR)
        if not backup_path.exists:
            create_full_path_dir(backup_path)
        self.app = app
        HiveInternal.mode = mode

    def backup_save_finish(self):
        did, content, err = did_post_json_param_pre_proc(self.response, "checksum_list")
        if err:
            return err

        checksum_list = content["checksum_list"]
        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            return self.response.response_err(NOT_FOUND, f"{did} backup vault not found")

        backup_checksum_list = get_file_checksum_list(backup_path)
        for checksum in checksum_list:
            if checksum not in backup_checksum_list:
                return self.response.response_err(CHECKSUM_FAILED, f"{did} backup file checksum failed")

        total_size = 0.0
        total_size = get_dir_size(backup_path.as_posix(), total_size)
        update_vault_backup_service_item(did, VAULT_BACKUP_SERVICE_USE_STORAGE, total_size)
        return self.response.response_ok()

    def backup_restore_finish(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return err

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            return self.response.response_err(NOT_FOUND, f"{did} backup vault not found")

        backup_checksum_list = get_file_checksum_list(backup_path)
        data = {"checksum_list": backup_checksum_list}
        return self.response.response_ok(data)

    def get_backup_service(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return self.response.response_err(UNAUTHORIZED, "Backup internal backup_communication_start auth failed")

        # check backup service exist
        info = get_vault_backup_service(did)
        if not info:
            return self.response.response_err(BAD_REQUEST, "There is no backup service of " + did)

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            create_full_path_dir(backup_path)

        del info["_id"]

        data = {"backup_service": info}
        return self.response.response_ok(data)

    def get_backup_files(self):
        did, content, err = did_post_json_param_pre_proc(self.response)
        if err:
            return self.response.response_err(UNAUTHORIZED, "Backup internal get_transfer_files auth failed")

        ret, message = can_access_backup(did)
        if ret != SUCCESS:
            return self.response.response_err(ret, "Backup internal get_transfer_files no backup failed")

        backup_path = get_vault_backup_path(did)
        if not backup_path.exists():
            self.response.response_ok({"backup_files": list()})

        file_md5_gene = deal_dir(backup_path.as_posix(), get_file_md5_info)
        file_md5_list = list()
        for md5 in file_md5_gene:
            md5_info = [md5[0], Path(md5[1]).relative_to(backup_path)]
            file_md5_list.append(md5_info)
        return self.response.response_ok({"backup_files": file_md5_list})

    def put_file(self, file_name):
        did, app_id, response = pre_proc(self.response, access_backup=BACKUP_ACCESS)
        if response is not None:
            return response

        file_name = filter_path_root(file_name)

        backup_path = get_vault_backup_path(did)
        full_path_name = (backup_path / file_name).resolve()

        if not full_path_name.parent.exists():
            if not create_full_path_dir(full_path_name.parent):
                return self.response.response_err(SERVER_MKDIR_ERROR,
                                                  "internal put_file error to create dir:" + full_path_name.parent.as_posix())

        temp_file = gene_temp_file_name()
        try:
            with open(temp_file, "bw") as f:
                chunk_size = CHUNK_SIZE
                while True:
                    chunk = request.stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
        except Exception as e:
            logger.error(f"exception of put_file error is {str(e)}")
            return self.response.response_err(SERVER_SAVE_FILE_ERROR, f"Exception: {str(e)}")

        if full_path_name.exists():
            full_path_name.unlink()
        shutil.move(temp_file.as_posix(), full_path_name.as_posix())
        return self.response.response_ok()

    def __get_file_check(self, resp):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            resp.status_code = UNAUTHORIZED
            return resp, None
        r, msg = can_access_backup(did)
        if r != SUCCESS:
            resp.status_code = r
            return resp, None

        file_name = request.args.get('file')
        file_name = filter_path_root(file_name)
        backup_path = get_vault_backup_path(did)
        file_full_name = (backup_path / file_name).resolve()

        if not file_full_name.exists():
            resp.status_code = NOT_FOUND
            return resp, None

        if not file_full_name.is_file():
            resp.status_code = FORBIDDEN
            return resp, None

        return resp, file_full_name

    def get_file(self):
        resp = Response()
        resp, file_full_name = self.__get_file_check(resp)
        if not file_full_name:
            return resp

        size = file_full_name.stat().st_size
        with open(file_full_name, 'rb') as f:
            etag = RangeRequest.make_etag(f)
        last_modified = datetime.utcnow()

        data = RangeRequest(open(file_full_name, 'rb'),
                            etag=etag,
                            last_modified=last_modified,
                            size=size).make_response()
        return data

    def move_file(self, is_copy):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "src_file", "dst_file",
                                                                  access_backup=BACKUP_ACCESS)
        if response is not None:
            return response

        src_name = content.get('src_file')
        src_name = filter_path_root(src_name)

        dst_name = content.get('dst_file')
        dst_name = filter_path_root(dst_name)

        backup_path = get_vault_backup_path(did)

        src_full_path_name = (backup_path / src_name).resolve()
        dst_full_path_name = (backup_path / dst_name).resolve()

        if not src_full_path_name.exists():
            return self.response.response_err(NOT_FOUND, "src_name not exists")

        if dst_full_path_name.exists():
            dst_full_path_name.unlink()

        dst_parent_folder = dst_full_path_name.parent
        if not dst_parent_folder.exists():
            if not create_full_path_dir(dst_parent_folder):
                return self.response.response_err(SERVER_MKDIR_ERROR, "move_file make dst parent path dir error")
        try:
            if is_copy:
                shutil.copy2(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
            else:
                shutil.move(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
        except Exception as e:
            logger.error(f"exception of move_file error is {str(e)}")
            return self.response.response_err(SERVER_MOVE_FILE_ERROR, "Exception:" + str(e))

        return self.response.response_ok()

    def delete_file(self):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "file_name",
                                                                  access_backup=BACKUP_ACCESS)
        if response is not None:
            return response

        file_name = content.get('file_name')
        file_name = filter_path_root(file_name)

        backup_path = get_vault_backup_path(did)
        full_path_name = (backup_path / file_name).resolve()

        if full_path_name.exists():
            full_path_name.unlink()
        # todo delete all empty path dir
        return self.response.response_ok()

    def get_file_patch_hash(self):
        resp = Response()
        resp, file_full_name = self.__get_file_check(resp)
        if not file_full_name:
            return resp

        open_file = open(file_full_name, 'rb')
        resp = Response(gene_blockchecksums(open_file, blocksize=CHUNK_SIZE))
        resp.status_code = SUCCESS
        return resp

    def patch_file_delta(self):
        resp = Response()
        resp, file_full_name = self.__get_file_check(resp)
        if not file_full_name:
            return resp

        patch_delta_file = gene_temp_file_name()
        try:
            with open(patch_delta_file, "bw") as f:
                chunk_size = CHUNK_SIZE
                while True:
                    chunk = request.stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
        except Exception as e:
            logger.error(f"exception of post_file_patch_delta read error is {str(e)}")
            resp.status_code = SERVER_SAVE_FILE_ERROR
            return resp

        with open(patch_delta_file, "rb") as f:
            delta_list = pickle.load(f)

        try:
            new_file = gene_temp_file_name()
            with open(file_full_name, "br") as unpatched:
                with open(new_file, "bw") as save_to:
                    unpatched.seek(0)
                    patchstream(unpatched, save_to, delta_list)
            patch_delta_file.unlink()
            if file_full_name.exists():
                file_full_name.unlink()
            shutil.move(new_file.as_posix(), file_full_name.as_posix())
        except Exception as e:
            logger.error(f"exception of post_file_patch_delta patch error is {str(e)}")
            resp.status_code = SERVER_PATCH_FILE_ERROR
            return resp

        resp.status_code = SUCCESS
        return resp
