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

    def get(self, url, access_token, is_body=True, options=None):
        try:
            headers = {"Content-Type": "application/json", "Authorization": "token " + access_token}
            r = requests.get(url, headers=headers, **(options if options else {}))
            if r.status_code != 200:
                raise InvalidParameterException(msg=f'[HttpClient] Failed to GET ({url}) with status code: {r.status_code}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(msg=f'[HttpClient] Failed to GET ({url}) with exception: {str(e)}')

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
            if r.status_code != 201:
                raise InvalidParameterException(
                    f'Failed to POST with status code: {r.status_code}, {r.text}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(f'Failed to POST with exception: {str(e)}')

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
            if r.status_code != 200:
                raise InvalidParameterException(f'Failed to PUT {url} with status code: {r.status_code}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT {url} with exception: {str(e)}')

    def put_file(self, url, access_token, file_path: Path):
        with open(file_path.as_posix(), 'br') as f:
            self.put(url, access_token, f, is_body=False)

    def delete(self, url, access_token):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.delete(url, headers=headers)
            if r.status_code != 204:
                raise InvalidParameterException(f'Failed to PUT with status code: {r.status_code}')
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT with exception: {str(e)}')


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
