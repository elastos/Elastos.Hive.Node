# -*- coding: utf-8 -*-
import datetime
import os
from pathlib import Path

import json
import requests

from src.utils.did.entity import Entity
from src.utils.singleton import Singleton
from src.utils.did.did_wrapper import JWT, Credential, DID
from tests import test_log
from tests.utils.resp_asserter import RA


BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class UserDID(Entity):
    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase)

    def issue_auth(self, app: 'AppDID') -> Credential:
        props = {'appDid': AppDID.app_did}
        return super().create_credential('AppIdCredential', props, owner_did=app.did)

    def issue_backup_auth(self, host_did: str, backup_url, backup_did) -> Credential:
        props = {'sourceHiveNodeDID': host_did, 'targetHiveNodeDID': backup_did, 'targetNodeURL': backup_url}
        return super().create_credential('HiveBackupCredential', props, owner_did=DID.from_string(host_did))

    def get_owner_credential(self, owner_did: DID) -> str:
        vc: Credential = super().create_credential('HiveNodeOwnerCredential', {}, owner_did=owner_did)
        return str(vc)


class AppDID(Entity):
    access_token = "123"
    app_did = "did:elastos:ienWaA6sfWETz6gVzX78SNytx8VUwDzxai"

    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase, need_resolve=False)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token


class TokenCache:
    enabled = True

    # tokens cache for every user did.

    @staticmethod
    def __get_token_cache_file_path(user_did: str, app_did: str):
        user_part = user_did.split(":")[2]
        parts = app_did.split(':')
        app_part = app_did if len(parts) < 3 else app_did.split(":")[2]

        file_name = f'{user_part}-{app_part}'

        return os.path.join(BASE_DIR, f'../../data/{file_name}')

    @staticmethod
    def save_token(user_did: str, app_did: str, token):
        if not TokenCache.enabled:
            return

        with open(TokenCache.__get_token_cache_file_path(user_did, app_did), 'w') as f:
            f.write(token)
            f.flush()

    @staticmethod
    def load_token(user_did: str, app_did: str):
        if not TokenCache.enabled:
            return None

        # try load token
        token_file = TokenCache.__get_token_cache_file_path(user_did, app_did)
        if not Path(token_file).exists():
            return None
        with open(token_file, 'r') as f:
            token = f.read()

        # remove if expired
        try:
            jwt = JWT.parse(token)
            if jwt.get_expiration() < int(datetime.datetime.now().timestamp()):
                os.unlink(token_file)
                return None
        except:
            # expired with exception
            os.unlink(token_file)
            return None

        return token

    # the node did of the connected hive node.

    @staticmethod
    def get_node_did_file_path():
        return os.path.join(BASE_DIR, '../../data/node_did')

    @staticmethod
    def save_node_did(node_did):
        if not TokenCache.enabled:
            return
        with open(TokenCache.get_node_did_file_path(), 'w') as f:
            f.write(node_did)
            f.flush()

    @staticmethod
    def get_node_did():
        if not TokenCache.enabled:
            return ''
        file_path = TokenCache.get_node_did_file_path()
        if not Path(file_path).exists():
            return ''
        with open(file_path, 'r') as f:
            return f.read()


class TestConfig(metaclass=Singleton):
    def __init__(self):
        self.net_work = 'local'  # TODO: 'local', 'testnet'
        if self.net_work == 'local':
            hive_port = os.environ.get('HIVE_PORT', 5000)
            test_log(f'HIVE_PORT={hive_port}')
            self.url_vault = f'http://localhost:{hive_port}'
        elif self.net_work == 'testnet':
            self.url_vault = f'https://hive-testnet1.trinity-tech.io'
        self.url_backup = self.url_vault

    @property
    def host_url(self):
        return self.url_vault

    @property
    def backup_url(self):
        return self.url_backup


class RemoteResolver:
    def __init__(self, http_client, is_did2=False, is_owner=False):
        """ For HttpClient and only manage DIDs. """
        self.app_did = AppDID("testapp", "chimney limit involve fine absent topic catch chalk goat era suit leisure")

        # user_did or user_did2 is as the user did
        # did: did:elastos:imedtHyjLS155Gedhv7vKP3FTWjpBUAUm4
        self.user_did = UserDID("didapp", "firm dash language credit twist puzzle crouch order slim now issue trap")
        self.user_did2 = UserDID("crossUser", "stage west lava group genre ten farm pony small family february drink")

        # this should be setup to the owner of the node (here is just simplify)
        self.owner_did = self.user_did

        self.test_config = TestConfig()
        self.http_client = http_client
        self.is_did2 = is_did2  # True means use user_did2
        self.is_owner = is_owner  # True means owner_did

    def get_token(self):
        user_did = self.get_current_user_did()
        token = TokenCache.load_token(user_did.get_did_string(), self.app_did.get_did_string())
        if not token:
            token = self.__get_access_token_from_remote(user_did)
            TokenCache.save_token(user_did.get_did_string(), self.app_did.get_did_string(), token)
        return token

    def get_current_user_did(self):
        return self.owner_did if self.is_owner else (self.user_did2 if self.is_did2 else self.user_did)

    def get_current_user_did_str(self):
        return self.get_current_user_did().get_did_string()

    def get_user_did_str(self):
        return self.user_did.get_did_string()

    def __get_access_token_from_remote(self, user_did: UserDID):
        return self.auth(self.sign_in(), user_did)

    def get_node_did(self) -> str:
        node_did = TokenCache.get_node_did()
        if node_did:
            return node_did

        challenge = self.sign_in()
        return self.__get_issuer_by_challenge(JWT.parse(challenge))

    def __get_issuer_by_challenge(self, jwt: JWT):
        node_did = str(jwt.get_issuer())
        TokenCache.save_node_did(node_did)
        return node_did

    def sign_in(self):
        doc = json.loads(self.app_did.doc.to_json())
        response = self.http_client.post('/api/v2/did/signin', body={"id": doc}, need_token=False, is_skip_prefix=True)
        RA(response).assert_status(201)
        return RA(response).body().get('challenge', str)

    def __get_challenge_response(self, challenge, user_did: UserDID) -> str:
        jwt = JWT.parse(challenge)
        assert jwt.get_audience() == self.app_did.get_did_string()
        nonce = jwt.get_claim('nonce')
        assert abs(jwt.get_expiration() - int(datetime.datetime.now().timestamp()) - 3 * 60) < 5 * 60, 'Invalid expire time setting for challenge'
        hive_did = self.__get_issuer_by_challenge(jwt)

        # auth
        vc = user_did.issue_auth(self.app_did)
        vp_json = self.app_did.create_presentation_str(vc, nonce, hive_did)
        expire = int(datetime.datetime.now().timestamp()) + 60
        return self.app_did.create_vp_token(vp_json, "DIDAuthResponse", hive_did, expire)

    def auth(self, challenge, user_did: UserDID):
        challenge_response = self.__get_challenge_response(challenge, user_did)
        response = self.http_client.post('/api/v2/did/auth', body={"challenge_response": challenge_response},
                                         need_token=False, is_skip_prefix=True)
        RA(response).assert_status(201)
        token = RA(response).body().get('token', str)
        jwt = JWT.parse(token)
        assert abs(jwt.get_expiration() - int(datetime.datetime.now().timestamp()) - 7 * 24 * 3600) < 5 * 60, 'Invalid expire time setting for token'
        return token

    def get_backup_credential(self, backup_node_did):
        """ INFO: current url to backup url and node did. """
        vc = self.get_current_user_did().issue_backup_auth(self.get_node_did(),
                                                           self.test_config.backup_url,
                                                           backup_node_did)
        return str(vc)


def _log_http_request(func):
    def wrapper(self, *args, **kwargs):
        method, full_url = func.__name__.upper(), self.get_full_url(args[0], kwargs.get("is_skip_prefix", False))
        test_log(f'\nREQUEST: {method}, {full_url}, kwargs={kwargs}')
        response = func(self, *args, **kwargs)
        test_log(f'RESPONSE: {method}, {full_url}, STATUS={response.status_code}, BODY={response.text}')
        return response
    return wrapper


class HttpClient:
    def __init__(self, prefix_url='', is_did2=False, is_owner=False, is_backup_node=False):
        """ For user and only manage vault or backup url accessing. """
        test_config = TestConfig()
        self.base_url = test_config.host_url if not is_backup_node else test_config.backup_url
        self.prefix_url = prefix_url if prefix_url else ''
        self.remote_resolver = RemoteResolver(self, is_did2, is_owner)
        test_log(f'HttpClient.base_url: {self.base_url}, user_did={self.get_current_did()}, app_did={AppDID.app_did}')

    def get_full_url(self, relative_url, is_skip_prefix=False):
        """ 'public' is for decorator '_log_http_request' """
        if is_skip_prefix:
            return self.base_url + relative_url
        return self.base_url + self.prefix_url + relative_url

    def __get_headers(self, need_token=True, is_json=True):
        headers = {}
        if is_json:
            headers['Content-type'] = 'application/json'
        if need_token:
            headers['Authorization'] = 'token ' + self.remote_resolver.get_token()
        test_log(f'HEADER: {headers}')
        return headers

    def get_current_did(self) -> str:
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
            return requests.get(self.get_full_url(relative_url),
                                headers=self.__get_headers(is_json=False, need_token=need_token), data=body)
        return requests.get(self.get_full_url(relative_url),
                            headers=self.__get_headers(need_token=need_token), json=body)

    @_log_http_request
    def post(self, relative_url, body=None, need_token=True, is_json=True, is_skip_prefix=False):
        if not is_json:
            return requests.post(self.get_full_url(relative_url, is_skip_prefix),
                                 headers=self.__get_headers(need_token=need_token, is_json=False), data=body)
        return requests.post(self.get_full_url(relative_url, is_skip_prefix),
                             headers=self.__get_headers(need_token=need_token), json=body)

    @_log_http_request
    def put(self, relative_url, body=None, is_json=True, need_token=True):
        if not is_json:
            return requests.put(self.get_full_url(relative_url), headers=self.__get_headers(is_json=False, need_token=need_token), data=body)
        return requests.put(self.get_full_url(relative_url), headers=self.__get_headers(), json=body)

    @_log_http_request
    def patch(self, relative_url, body=None, need_token=True):
        return requests.patch(self.get_full_url(relative_url), headers=self.__get_headers(need_token=need_token), json=body)

    @_log_http_request
    def delete(self, relative_url, body=None, is_json=False):
        if not is_json:
            return requests.delete(self.get_full_url(relative_url), headers=self.__get_headers(is_json=False), data=body)
        return requests.delete(self.get_full_url(relative_url), headers=self.__get_headers(), json=body)
