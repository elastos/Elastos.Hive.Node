# -*- coding: utf-8 -*-

"""
Http client for backup or other modules.
"""
import requests

from src.utils.http_response import InvalidParameterException


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

    def post(self, url, access_token, body, is_json=True, is_body=True):
        try:
            headers = dict()
            if access_token:
                headers["Authorization"] = "token " + access_token
            if is_json:
                headers['Content-Type'] = 'application/json'
            r = requests.post(url, headers=headers, json=body) \
                if is_json else requests.post(url, headers=headers, data=body)
            if r.status_code != 201:
                raise InvalidParameterException(f'Failed to POST with status code: {r.status_code}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(f'Failed to POST with exception: {str(e)}')

    def put(self, url, access_token, body, is_body=False):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.put(url, headers=headers, data=body)
            if r.status_code != 200:
                raise InvalidParameterException(f'Failed to PUT {url} with status code: {r.status_code}')
            return r.json() if is_body else r
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT {url} with exception: {str(e)}')

    def delete(self, url, access_token):
        try:
            headers = {"Authorization": "token " + access_token}
            r = requests.delete(url, headers=headers)
            if r.status_code != 204:
                raise InvalidParameterException(f'Failed to PUT with status code: {r.status_code}')
        except Exception as e:
            raise InvalidParameterException(f'Failed to PUT with exception: {str(e)}')
