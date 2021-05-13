# -*- coding: utf-8 -*-

import requests
import json

from hive.util.did.eladid import ffi, lib

from tests_v1.hive_auth_test import DApp, DIDApp
from tests_v1 import test_common


class RemoteResolver:
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
        # if not jws:
        #     print(ffi.string(lib.DIDError_GetMessage()).decode())
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
        return response.json()["auth_token"]


class HttpClient:
    def __init__(self, base_url):
        self.base_url = base_url
        # self.token = 'eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aW9SbjNlRW9wUmpBN0NCUnJyV1FXenR0QWZYQWp6dktNeCNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3Rvczppb1JuM2VFb3BSakE3Q0JScnJXUVd6dHRBZlhBanp2S014Iiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppWllEVVY3R3ZoWXB2UHAxYWljMXBlcU1WZDNyYXF0SGkyIiwiZXhwIjoxNjIyMTAxNTI5LCJwcm9wcyI6IntcImFwcERpZFwiOiBcImFwcElkXCIsIFwidXNlckRpZFwiOiBcImRpZDplbGFzdG9zOmlxazNLTGViZ2lpUDQ2dXlvS2V2WVFKQjdQWmNzMmlUTHpcIiwgXCJub25jZVwiOiBcIjcyOTRlMjE0LWE3MmMtMTFlYi1hOGU0LWFjZGU0ODAwMTEyMlwifSJ9.Xox6tzUd3FXIqtv8J1S_nylL0tdy-IaYTDAB5JoHLLdXxIA6h917KQm1s8l8Rx5lPh7PXVQu-p3Zkuu6ym5DfA'
        self.remote_resolver = RemoteResolver()

    def __get_url(self, relative_url):
        return self.base_url + relative_url

    def __get_headers(self):
        return {'Authorization': 'token ' + self.remote_resolver.get_token()}

    def get(self, relative_url):
        return requests.get(self.__get_url(relative_url), headers=self.__get_headers())

    def post(self, relative_url, body, need_token=True):
        return requests.post(self.__get_url(relative_url),
                             headers=self.__get_headers() if need_token else {},
                             data=body)

    def put(self, relative_url, body):
        return requests.put(self.__get_url(relative_url), headers=self.__get_headers(), data=body)

    def patch(self, relative_url, body):
        return requests.patch(self.__get_url(relative_url), headers=self.__get_headers(), data=body)

    def delete(self, relative_url):
        return requests.delete(self.__get_url(relative_url), headers=self.__get_headers())
