from pathlib import Path

from src import hive_setting
from src.modules.files.local_file import LocalFile


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
