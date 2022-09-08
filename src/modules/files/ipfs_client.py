import json
import logging
import typing as t
from pathlib import Path

from src import hive_setting
from src.utils.http_exception import BadRequestException
from src.modules.files.local_file import LocalFile


def try_three_times(f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    """ try to call http related method 3 times. """
    def wrapper(*args, **kwargs):
        i, count = 1, 3
        while i <= count:
            try:
                return f(*args, **kwargs)
            except Exception as e:
                i += 1
    return wrapper


class IpfsClient:
    def __init__(self):
        self._http = None
        self.ipfs_url = hive_setting.IPFS_NODE_URL
        self.ipfs_gateway_url = hive_setting.IPFS_GATEWAY_URL

    @property
    def http(self):
        if not self._http:
            from src.utils.http_client import HttpClient
            self._http = HttpClient()
        return self._http

    def upload_file(self, file_path: Path):
        files = {'file': open(file_path.as_posix(), 'rb')}
        json_data = self.http.post(self.ipfs_url + '/api/v0/add', None, None, is_json=False, files=files, success_code=200)
        return json_data['Hash']

    @try_three_times
    def download_file(self, cid, file_path: Path, is_proxy=False, sha256=None, size=None):
        url = self.ipfs_gateway_url if is_proxy else self.ipfs_url
        response = self.http.post(f'{url}/api/v0/cat?arg={cid}', None, None, is_body=False, success_code=200)
        LocalFile.write_file_by_response(response, file_path)

        if size is not None:
            cid_size = file_path.stat().st_size
            if size != cid_size:
                return f'Failed to get file content with cid {cid}, size {size, cid_size}'

        if sha256:
            cid_sha256 = LocalFile.get_sha256(file_path.as_posix())
            if sha256 != cid_sha256:
                return f'Failed to get file content with cid {cid}, sha256 {sha256, cid_sha256}'

    def download_file_json_content(self, cid, is_proxy=False, sha256=None, size=None) -> dict:
        temp_file = LocalFile.generate_tmp_file_path()
        msg = self.download_file(cid, temp_file, is_proxy=is_proxy, sha256=sha256, size=size)
        if msg:
            temp_file.unlink()
            raise BadRequestException(msg)
        with temp_file.open() as f:
            metadata = json.load(f)
        temp_file.unlink()
        return metadata

    def cid_pin(self, cid):
        """ Pin file from ipfs proxy to the local node. """

        # INFO: IPFS does not support that one node directly pin file from other node.
        logging.info(f'[IpfsClient.cid_pin] Try to pin {cid} to the local IPFS node.')

        # download the file to local
        temp_file = LocalFile.generate_tmp_file_path()
        self.download_file(cid, temp_file, is_proxy=True)

        logging.info(f'[IpfsClient.cid_pin] Download file OK.')

        # then upload the file to local IPFS node.
        self.upload_file(temp_file)

        logging.info(f'[IpfsClient.cid_pin] Upload file OK.')

        # clean the local file.
        size = temp_file.stat().st_size
        temp_file.unlink()
        return size

    def cid_unpin(self, cid):
        logging.info(f'[IpfsClient.cid_unpin] Try to unpin {cid} in backup node.')

        if not self.cid_exists(cid):
            return

        try:
            response = self.http.post(self.ipfs_url + f'/api/v0/pin/rm?arg=/ipfs/{cid}&recursive=true', None, None, is_body=False, success_code=200)
        except BadRequestException as e:
            # skip this error
            if 'not pinned or pinned indirectly' not in e.msg:
                raise e

    def cid_exists(self, cid):
        try:
            response = self.http.post(f'{self.ipfs_url}/api/v0/cat?arg={cid}', None, None, is_body=False, success_code=200)
            return True
        except BadRequestException as e:
            return False
