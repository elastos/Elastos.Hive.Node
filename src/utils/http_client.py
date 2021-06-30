# -*- coding: utf-8 -*-

"""
Http client for backup or other modules.
"""
import pickle
from datetime import datetime
from pathlib import Path

import requests

from hive.util.flask_rangerequest import RangeRequest
from src.utils.file_manager import fm
from src.utils.http_exception import InvalidParameterException, FileNotFoundException


class HttpClient:
    def __init__(self):
        pass

    def _check_status_code(self, r, expect_code):
        if r.status_code != expect_code:
            raise InvalidParameterException(msg=f'[HttpClient] Failed to {r.request.method} ({r.request.url}) '
                                                f'with status code: {r.status_code}, {r.text}')

    def _raise_http_exception(self, url, method, e):
        raise InvalidParameterException(msg=f'[HttpClient] Failed to {method} ({url}) with exception: {str(e)}')

    def get(self, url, access_token, is_body=True, options=None):
        try:
            headers = {"Content-Type": "application/json", "Authorization": "token " + access_token}
            r = requests.get(url, headers=headers, **(options if options else {}))
            self._check_status_code(r, 200)
            return r.json() if is_body else r
        except Exception as e:
            self._raise_http_exception(url, 'GET', e)

    def get_to_file(self, url, access_token, file_path: Path):
        r = self.get(url, access_token, is_body=False, options={'stream': True})
        fm.write_file_by_response(r, file_path, is_temp=True)

    def post(self, url, access_token, body, is_json=True, is_body=True, options=None):
        try:
            headers = dict()
            if access_token:
                headers["Authorization"] = "token " + access_token
            if is_json:
                headers['Content-Type'] = 'application/json'
            r = requests.post(url, headers=headers, json=body, **(options if options else {})) \
                if is_json else requests.post(url, headers=headers, data=body, **(options if options else {}))
            self._check_status_code(r, 201)
            return r.json() if is_body else r
        except Exception as e:
            self._raise_http_exception(url, 'POST', e)

    def post_file(self, url, access_token, file_path: str):
        with open(file_path, 'rb') as f:
            self.post(url, access_token, body=f, is_json=False, is_body=False)

    def post_to_file(self, url, access_token, file_path: Path, body=None, is_temp=False):
        r = self.post(url, access_token, body, is_json=False, is_body=False, options={'stream': True})
        fm.write_file_by_response(r, file_path, is_temp)

    def post_to_pickle_data(self, url, access_token, body=None):
        r = self.post(url, access_token, body, is_json=False, is_body=False, options={'stream': True})
        return pickle.loads(r.content)

    def put(self, url, access_token, body, is_body=False):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.put(url, headers=headers, data=body)
            self._check_status_code(r, 200)
            return r.json() if is_body else r
        except Exception as e:
            self._raise_http_exception(url, 'PUT', e)

    def put_file(self, url, access_token, file_path: Path):
        with open(file_path.as_posix(), 'br') as f:
            self.put(url, access_token, f, is_body=False)

    def delete(self, url, access_token):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.delete(url, headers=headers)
            self._check_status_code(r, 204)
        except Exception as e:
            self._raise_http_exception(url, 'DELETE', e)


class HttpServer:
    def __init__(self):
        pass

    def create_range_request(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundException(msg='Failed to get file for creating range request object.')

        with open(file_path.as_posix(), 'rb') as f:
            etag = RangeRequest.make_etag(f)
        return RangeRequest(open(file_path.as_posix(), 'rb'),
                            etag=etag,
                            last_modified=datetime.utcnow(),
                            size=file_path.stat().st_size).make_response()
