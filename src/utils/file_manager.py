# -*- coding: utf-8 -*-

"""
This is for files management, include file, file content, file properties, and dir management.
"""
import pickle
import shutil
from pathlib import Path

from flask import request

from hive.util.common import deal_dir, get_file_md5_info, create_full_path_dir, gene_temp_file_name
from hive.util.constants import CHUNK_SIZE
from hive.util.payment.vault_backup_service_manage import get_vault_backup_path
from hive.util.payment.vault_service_manage import get_vault_used_storage
from hive.util.pyrsync import rsyncdelta, gene_blockchecksums, patchstream
from src.utils.http_exception import BadRequestException


class FileManager:
    def __init__(self):
        pass

    def get_vault_storage_size(self, did):
        return get_vault_used_storage(did)

    def get_file_checksum_list(self, root_path: Path) -> list:
        """
        :return [(name, checksum), ...]
        """
        return list() if not root_path.exists() else \
            [(md5[0], Path(md5[1]).relative_to(root_path).as_posix())
                for md5 in deal_dir(root_path.as_posix(), get_file_md5_info)]

    def get_hashes_by_file(self, file_path: Path):
        if not file_path.exists():
            return ''
        hashes = ''
        with open(file_path.as_posix(), 'rb') as open_file:
            for h in gene_blockchecksums(open_file, blocksize=CHUNK_SIZE):
                hashes += h
        return hashes

    def get_hashes_by_lines(self, lines):
        hashes = list()
        for line in lines:
            if not line:
                continue
            parts = line.split(b',')
            hashes.append((int(parts[0].decode("utf-8")), parts[1].decode("utf-8")))
        return hashes

    def get_rsync_data(self, src_path: Path, target_hashes):
        with open(src_path.as_posix(), "rb") as f:
            patch_data = rsyncdelta(f, target_hashes, blocksize=CHUNK_SIZE)
        return pickle.dumps(patch_data)

    def apply_rsync_data(self, file_path: Path, data):
        def on_save_to_temp(temp_file):
            with open(file_path.as_posix(), "br") as f:
                with open(temp_file.as_posix(), "bw") as tmp_f:
                    f.seek(0)
                    patchstream(f, tmp_f, data)
        self.__save_with_temp_file(file_path, on_save_to_temp)

    def write_file_by_response(self, response, file_path: Path, is_temp=False):
        if not self.create_parent_dir(file_path):
            raise BadRequestException(msg=f'Failed to create parent folder for file {file_path.name}')

        if is_temp:
            def on_save_to_temp(temp_file):
                self.write_file_by_response(response, temp_file)
            self.__save_with_temp_file(file_path, on_save_to_temp)
        else:
            with open(file_path.as_posix(), 'bw') as f:
                f.seek(0)
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

    def write_file_by_request_stream(self, file_path: Path):
        if not self.create_parent_dir(file_path):
            raise BadRequestException(msg=f'Failed to create parent folder for file {file_path.name}.')

        def on_save_to_temp(temp_file):
            with open(temp_file.as_posix(), "bw") as f:
                while True:
                    chunk = request.stream.read(CHUNK_SIZE)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)

        self.__save_with_temp_file(file_path, on_save_to_temp)

    def write_file_by_rsync_data(self, data, file_path: Path):
        with open(file_path.as_posix(), "wb") as f:
            pickle.dump(data, f)

    def read_rsync_data_from_file(self, file_path: Path):
        with open(file_path.as_posix(), "rb") as f:
            return pickle.load(f)

    def create_parent_dir(self, file_path: Path):
        return self.create_dir(file_path.parent)

    def create_dir(self, path: Path):
        if not path.exists() and not create_full_path_dir(path):
            return False
        return True

    def __save_with_temp_file(self, file_path: Path, on_save_to_temp):
        temp_file = gene_temp_file_name()

        on_save_to_temp(temp_file)

        if file_path.exists():
            file_path.unlink()
        shutil.move(temp_file.as_posix(), file_path.as_posix())

    def delete_file(self, file_path: Path):
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    def delete_vault_file(self, did, name):
        self.delete_file((get_vault_backup_path(did) / name).resolve())


fm = FileManager()
