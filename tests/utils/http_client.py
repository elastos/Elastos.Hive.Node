# -*- coding: utf-8 -*-

import requests
import json
import logging

from hive.util.did.eladid import ffi, lib
from tests_v1.hive_auth_test import DApp, DIDApp
from tests_v1 import test_common


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RemoteResolver(metaclass=Singleton):
    def __init__(self):
        self.token = None
        self.user_did = DIDApp("didapp", "firm dash language credit twist puzzle crouch order slim now issue trap", "")
        self.app_did = DApp("testapp",
                            test_common.app_id,
                            "street shrug castle where muscle swift coin mirror exercise police toward boring", "")
        self.http_client = HttpClient('http://localhost:5000/api/v1/did')

    def get_token(self):
        if not self.token:
            self.token = self.__get_remote_token()
        return self.token

    def __get_remote_token(self):
        return self.auth(self.sign_in())

    def sign_in(self):
        doc_c = lib.DIDStore_LoadDID(self.app_did.store, self.app_did.did)
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc_c, True)).decode()
        doc = json.loads(doc_str)
        response = self.http_client.post('/sign_in', json.dumps({"document": doc}), need_token=False)
        assert response.status_code == 200
        assert response.json()["_status"] == 'OK'
        return response.json()["challenge"]

    def __get_auth_token(self, challenge):
        jws = lib.DefaultJWSParser_Parse(challenge.encode())
        if not jws:
            print(ffi.string(lib.DIDError_GetMessage()).decode())
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        assert aud == self.app_did.get_did_string()
        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        hive_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)

        # auth
        vc = self.user_did.issue_auth(self.app_did)
        vp_json = self.app_did.create_presentation(vc, nonce, hive_did)
        return self.app_did.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)

    def auth(self, challenge):
        auth_token = self.__get_auth_token(challenge)
        response = self.http_client.post('/auth', json.dumps({"jwt": auth_token}), need_token=False)
        assert response.status_code == 200
        assert response.json()["_status"] == 'OK'
        return response.json()["access_token"]


def _log_http_request(func):
    def wrapper(self, *args, **kwargs):
        logging.debug(f'REQUEST:{func.__name__},{args},{kwargs}')
        response = func(self, *args, **kwargs)
        logging.debug(f'RESPONSE:{func.__name__},{response.status_code},{response.text}')
        return response
    return wrapper


class HttpClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.remote_resolver = None

    def __get_url(self, relative_url):
        return self.base_url + relative_url

    def __get_headers(self, need_token=True):
        headers = {'Content-type': 'application/json'}
        if need_token:
            headers['Authorization'] = 'token ' + RemoteResolver().get_token()
        return headers

    @_log_http_request
    def get(self, relative_url):
        return requests.get(self.__get_url(relative_url), headers=self.__get_headers())

    @_log_http_request
    def post(self, relative_url, body, need_token=True):
        return requests.post(self.__get_url(relative_url), headers=self.__get_headers(need_token), data=body)

    @_log_http_request
    def put(self, relative_url, body):
        return requests.put(self.__get_url(relative_url), headers=self.__get_headers(), json=body)

    @_log_http_request
    def patch(self, relative_url, body):
        return requests.patch(self.__get_url(relative_url), headers=self.__get_headers(), json=body)

    @_log_http_request
    def delete(self, relative_url):
        return requests.delete(self.__get_url(relative_url), headers=self.__get_headers())
