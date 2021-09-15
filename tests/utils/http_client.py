# -*- coding: utf-8 -*-

import requests
import json
import logging

from src.utils_v1.did.eladid import ffi, lib
from src.utils.singleton import Singleton
from tests.utils_v1.hive_auth_test_v1 import DApp, DIDApp
from tests.utils_v1 import test_common


class TestConfig(metaclass=Singleton):
    def __init__(self):
        self.url_vault = 'http://localhost:5000'
        self.url_backup = 'http://localhost:5000'
        # self.url_vault = 'https://hive-testnet1.trinity-tech.io'
        # self.url_backup = 'https://hive-testnet2.trinity-tech.io'
        self.node_did_cache = dict()
        self.token_cache = dict()

    @property
    def host_url(self):
        return self.url_vault

    @property
    def backup_url(self):
        return self.url_backup

    def save_token(self, base_url, user_did, token):
        self.token_cache[self._get_key_for_token_cache(base_url, user_did)] = token

    def get_token(self, base_url, user_did):
        return self.token_cache.get(self._get_key_for_token_cache(base_url, user_did))

    def _get_key_for_token_cache(self, base_url, user_did):
        return f'{user_did}@{base_url}'

    def save_node_did(self, base_url, node_did):
        self.node_did_cache[base_url] = node_did

    def get_node_did(self, base_url):
        return self.node_did_cache.get(base_url)


class RemoteResolver:
    def __init__(self, http_client, is_did2=False):
        """ For HttpClient and only manage DIDs. """
        self.user_did = DIDApp("didapp", "firm dash language credit twist puzzle crouch order slim now issue trap")
        self.user_did2 = DIDApp("crossUser",
                                "stage west lava group genre ten farm pony small family february drink")
        self.app_did = DApp("testapp", test_common.app_id,
                            "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        self.test_config = TestConfig()
        self.http_client = http_client
        self.is_did2 = is_did2

    def get_token(self):
        user_did = self.get_current_user_did()
        token = self.test_config.get_token(self.http_client.base_url, user_did)
        if not token:
            token = self.__get_remote_token(user_did)
            self.test_config.save_token(self.http_client.base_url, user_did, token)
        return token

    def get_current_user_did(self):
        return self.user_did2 if self.is_did2 else self.user_did

    def get_current_user_did_str(self):
        return self.get_current_user_did().get_did_string()

    def get_user_did_str(self):
        return self.user_did.get_did_string()

    def __get_remote_token(self, did: DIDApp):
        return self.auth(self.sign_in(), did)

    def get_node_did(self):
        node_did = self.test_config.get_node_did(self.http_client.base_url)
        if node_did:
            return node_did

        # get from the result of sign_in()
        challenge = self.sign_in()
        jws = lib.DefaultJWSParser_Parse(challenge.encode())
        assert jws, f'Cannot get challenge for node did: {ffi.string(lib.DIDError_GetLastErrorMessage()).decode()}'
        node_did = self.__get_issuer_by_challenge2(jws)
        lib.JWT_Destroy(jws)
        return node_did

    def __get_issuer_by_challenge2(self, jws):
        node_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        assert node_did, 'Invalid hive did'
        self.test_config.save_node_did(self.http_client.base_url, node_did)
        return node_did

    def sign_in(self):
        doc_c = lib.DIDStore_LoadDID(self.app_did.store, self.app_did.did)
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc_c, True)).decode()
        doc = json.loads(doc_str)
        response = self.http_client.post('/api/v2/did/signin', {"id": doc}, need_token=False, is_skip_prefix=True)
        assert response.status_code == 201
        return response.json()["challenge"]

    def __get_auth_token_by_challenge(self, challenge, did: DIDApp):
        jws = lib.DefaultJWSParser_Parse(challenge.encode())
        assert jws, f'Cannot get challenge: {ffi.string(lib.DIDError_GetLastErrorMessage()).decode()}'
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        assert aud == self.app_did.get_did_string()
        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        hive_did = self.__get_issuer_by_challenge2(jws)
        lib.JWT_Destroy(jws)

        # auth
        vc = did.issue_auth(self.app_did)
        vp_json = self.app_did.create_presentation(vc, nonce, hive_did)
        return self.app_did.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)

    def auth(self, challenge, did: DIDApp):
        auth_token = self.__get_auth_token_by_challenge(challenge, did)
        response = self.http_client.post('/api/v2/did/auth', {"challenge_response": auth_token},
                                         need_token=False, is_skip_prefix=True)
        assert response.status_code == 201
        return response.json()["token"]

    def get_backup_credential(self, backup_node_did):
        """ INFO: current url to backup url and node did. """
        vc = self.get_current_user_did().issue_backup_auth(self.get_node_did(),
                                                           self.test_config.backup_url,
                                                           backup_node_did)
        return ffi.string(lib.Credential_ToString(vc, True)).decode()


def _log_http_request(func):
    def wrapper(self, *args, **kwargs):
        logging.debug(f'REQUEST:{func.__name__},{args},{kwargs}')
        response = func(self, *args, **kwargs)
        logging.debug(f'RESPONSE:{func.__name__},{response.status_code},{response.text}')
        return response
    return wrapper


class HttpClient:
    def __init__(self, prefix_url='', is_did2=False, is_backup_node=False):
        """ For user and only manage vault or backup url accessing. """
        test_config = TestConfig()
        self.base_url = test_config.host_url if not is_backup_node else test_config.backup_url
        self.prefix_url = prefix_url if prefix_url else ''
        self.is_did2 = is_did2
        self.remote_resolver = RemoteResolver(self, is_did2)
        logging.debug(f'HttpClient.base_url: {self.base_url}')

    def __get_url(self, relative_url, is_skip_prefix=False):
        if is_skip_prefix:
            return self.base_url + relative_url
        return self.base_url + self.prefix_url + relative_url

    def __get_headers(self, need_token=True, is_json=True):
        headers = {}
        if is_json:
            headers['Content-type'] = 'application/json'
        if need_token:
            headers['Authorization'] = 'token ' + self.remote_resolver.get_token()
        logging.debug(f'HEADER: {headers}')
        return headers

    def get_current_did(self):
        return self.remote_resolver.get_current_user_did_str()

    @staticmethod
    def get_backup_node_did():
        client = HttpClient(is_backup_node=True)
        return client.remote_resolver.get_node_did()

    def get_backup_credential(self):
        return self.remote_resolver.get_backup_credential(self.__class__.get_backup_node_did())

    @_log_http_request
    def get(self, relative_url, body=None, is_json=False, need_token=True):
        if not is_json:
            return requests.get(self.__get_url(relative_url),
                                headers=self.__get_headers(is_json=False, need_token=need_token), data=body)
        return requests.get(self.__get_url(relative_url),
                            headers=self.__get_headers(need_token=need_token), json=body)

    @_log_http_request
    def post(self, relative_url, body=None, need_token=True, is_json=True, is_skip_prefix=False):
        if not is_json:
            return requests.post(self.__get_url(relative_url, is_skip_prefix),
                                 headers=self.__get_headers(need_token=need_token, is_json=False), data=body)
        return requests.post(self.__get_url(relative_url, is_skip_prefix),
                             headers=self.__get_headers(need_token=need_token), json=body)

    @_log_http_request
    def put(self, relative_url, body=None, is_json=True):
        if not is_json:
            return requests.put(self.__get_url(relative_url), headers=self.__get_headers(is_json=False), data=body)
        return requests.put(self.__get_url(relative_url), headers=self.__get_headers(), json=body)

    @_log_http_request
    def patch(self, relative_url, body=None):
        return requests.patch(self.__get_url(relative_url), headers=self.__get_headers(), json=body)

    @_log_http_request
    def delete(self, relative_url, body=None, is_json=False):
        if not is_json:
            return requests.delete(self.__get_url(relative_url), headers=self.__get_headers(is_json=False), data=body)
        return requests.delete(self.__get_url(relative_url), headers=self.__get_headers(), json=body)
