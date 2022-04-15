# -*- coding: utf-8 -*-
import os

import requests
import json
import logging

from src.utils.singleton import Singleton
from src.utils.did.did_wrapper import JWT
from tests.utils_v1.hive_auth_test_v1 import AppDID, UserDID


class TestConfig(metaclass=Singleton):
    def __init__(self):
        hive_port = os.environ.get('HIVE_PORT', 5000)
        self.url_vault = f'http://localhost:{hive_port}'
        self.url_backup = f'http://localhost:{hive_port}'
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
    def __init__(self, http_client, is_did2=False, is_owner=False):
        """ For HttpClient and only manage DIDs. """
        # did: did:elastos:imedtHyjLS155Gedhv7vKP3FTWjpBUAUm4
        self.user_did = UserDID("didapp", "firm dash language credit twist puzzle crouch order slim now issue trap")
        self.user_did2 = UserDID("crossUser", "stage west lava group genre ten farm pony small family february drink")
        self.owner_did = self.user_did
        self.app_did = AppDID("testapp", "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        self.test_config = TestConfig()
        self.http_client = http_client
        self.is_did2 = is_did2
        self.is_owner = is_owner

    def get_token(self):
        user_did = self.get_current_user_did()
        # token = self.test_config.get_token(self.http_client.base_url, user_did)
        # if not token:
        #     token = self.__get_remote_token(user_did)
        #     self.test_config.save_token(self.http_client.base_url, user_did, token)
        token = self._get_remote_token(user_did)
        # print(f'API token: {token}')
        return token

    def get_current_user_did(self):
        return self.owner_did if self.is_owner else (self.user_did2 if self.is_did2 else self.user_did)

    def get_current_user_did_str(self):
        return self.get_current_user_did().get_did_string()

    def get_user_did_str(self):
        return self.user_did.get_did_string()

    def _get_remote_token(self, did: UserDID):
        return self.auth(self.sign_in(), did)

    def get_node_did(self) -> str:
        node_did = self.test_config.get_node_did(self.http_client.base_url)
        if node_did:
            return node_did

        # get from the result of sign_in()
        challenge = self.sign_in()
        return self._get_issuer_by_challenge(JWT.parse(challenge))

    def _get_issuer_by_challenge(self, jwt: JWT):
        node_did = str(jwt.get_issuer())
        self.test_config.save_node_did(self.http_client.base_url, node_did)
        return node_did

    def sign_in(self):
        doc = json.loads(self.app_did.doc.to_json())
        response = self.http_client.post('/api/v2/did/signin', {"id": doc}, need_token=False, is_skip_prefix=True)
        assert response.status_code == 201
        return response.json()["challenge"]

    def _get_auth_token_by_challenge(self, challenge, did: UserDID):
        jwt = JWT.parse(challenge)
        assert jwt.get_audience() == self.app_did.get_did_string()
        nonce = jwt.get_claim('nonce')
        hive_did = self._get_issuer_by_challenge(jwt)

        # auth
        vc = did.issue_auth(self.app_did)
        vp_json = self.app_did.create_presentation_str(vc, nonce, hive_did)
        return self.app_did.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)

    def auth(self, challenge, did: UserDID):
        challenge_response = self._get_auth_token_by_challenge(challenge, did)
        response = self.http_client.post('/api/v2/did/auth', {"challenge_response": challenge_response},
                                         need_token=False, is_skip_prefix=True)
        assert response.status_code == 201
        return response.json()["token"]

    def get_backup_credential(self, backup_node_did):
        """ INFO: current url to backup url and node did. """
        vc = self.get_current_user_did().issue_backup_auth(self.get_node_did(),
                                                           self.test_config.backup_url,
                                                           backup_node_did)
        return str(vc)


def _log_http_request(func):
    def wrapper(self, *args, **kwargs):
        logging.debug(f'REQUEST:{func.__name__},{args},{kwargs}')
        response = func(self, *args, **kwargs)
        logging.debug(f'RESPONSE:{func.__name__},{response.status_code},{response.text}')
        return response
    return wrapper


class HttpClient:
    def __init__(self, prefix_url='', is_did2=False, is_owner=False, is_backup_node=False):
        """ For user and only manage vault or backup url accessing. """
        test_config = TestConfig()
        self.base_url = test_config.host_url if not is_backup_node else test_config.backup_url
        self.prefix_url = prefix_url if prefix_url else ''
        self.remote_resolver = RemoteResolver(self, is_did2, is_owner)
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
