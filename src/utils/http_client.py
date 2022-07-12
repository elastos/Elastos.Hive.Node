# -*- coding: utf-8 -*-

"""
Http client for backup or other modules.
"""
import pickle
from pathlib import Path

import requests

from src.utils.file_manager import fm
from src.utils.http_exception import BadRequestException, HiveException


class HttpClient:
    def __init__(self):
        self.timeout = 30

    def __check_status_code(self, r, expect_code):
        if r.status_code != expect_code:
            msg = r.text
            try:
                body = r.json()
                msg = body['error']['message']
            except Exception as e:
                ...
            raise BadRequestException(f'[HttpClient] Failed to {r.request.method}, ({r.request.url}) '
                                          f'with status code: {r.status_code}, {msg}')

    def __raise_http_exception(self, url, method, e):
        raise BadRequestException(f'[HttpClient] Failed to {method}, ({url}) with exception: {str(e)}')

    def get(self, url, access_token, is_body=True, **kwargs):
        try:
            headers = {"Content-Type": "application/json", "Authorization": "token " + access_token}
            r = requests.get(url, headers=headers, timeout=self.timeout, **kwargs)
            self.__check_status_code(r, 200)
            return r.json() if is_body else r
        except HiveException as e:
            raise e
        except Exception as e:
            self.__raise_http_exception(url, 'GET', e)

    def get_to_file(self, url, access_token, file_path: Path):
        r = self.get(url, access_token, is_body=False, stream=True)
        fm.write_file_by_response(r, file_path, is_temp=True)

    def post(self, url, access_token, body, is_json=True, is_body=True, success_code=201, timeout=None, **kwargs):
        try:
            headers = dict()
            if access_token:
                headers["Authorization"] = "token " + access_token
            if is_json:
                headers['Content-Type'] = 'application/json'

            timeout_ = timeout if timeout is not None else self.timeout

            r = requests.post(url, headers=headers, json=body, timeout=timeout_, **kwargs) \
                if is_json else requests.post(url, headers=headers, data=body, timeout=self.timeout, **kwargs)
            self.__check_status_code(r, success_code)
            return r.json() if is_body else r
        except HiveException as e:
            raise e
        except Exception as e:
            self.__raise_http_exception(url, 'POST', e)

    def post_file(self, url, access_token, file_path: str):
        with open(file_path, 'rb') as f:
            self.post(url, access_token, body=f, is_json=False, is_body=False)

    def post_to_file(self, url, access_token, file_path: Path, body=None, is_temp=False):
        r = self.post(url, access_token, body, is_json=False, is_body=False, stream=True)
        fm.write_file_by_response(r, file_path, is_temp)

    def post_to_pickle_data(self, url, access_token, body=None):
        r = self.post(url, access_token, body, is_json=False, is_body=False, stream=True)
        return pickle.loads(r.content)

    def put(self, url, access_token, body, is_body=False):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.put(url, headers=headers, data=body, timeout=self.timeout)
            self.__check_status_code(r, 200)
            return r.json() if is_body else r
        except HiveException as e:
            raise e
        except Exception as e:
            self.__raise_http_exception(url, 'PUT', e)

    def put_file(self, url, access_token, file_path: Path):
        with open(file_path.as_posix(), 'br') as f:
            self.put(url, access_token, f, is_body=False)

    def delete(self, url, access_token):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.delete(url, headers=headers, timeout=self.timeout)
            self.__check_status_code(r, 204)
        except HiveException as e:
            raise e
        except Exception as e:
            self.__raise_http_exception(url, 'DELETE', e)
