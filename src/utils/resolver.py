# -*- coding: utf-8 -*-
import json
import logging

from src import init_did_backend
from src.utils.http_client import HttpClient
from src.utils.http_exception import BadRequestException
from src.utils_v1.did.eladid import ffi, lib


class ElaResolver:
    def __init__(self, base_url):
        self.base_url = base_url
        self.cli = HttpClient()

    def get_transaction_info(self, transaction_id):
        param = {"method": "getrawtransaction", "params": [transaction_id, True]}
        json_body = self.cli.post(self.base_url, None, param, success_code=200)
        if not isinstance(json_body, dict) or json_body['error'] is not None:
            raise BadRequestException(msg=f'Failed to get transaction info by error: {json_body["error"]}')
        return json_body['result']

    def hexstring_to_bytes(self, s: str, reverse=True):
        if reverse:
            return bytes(reversed([int(s[x:x + 2], 16) for x in range(0, len(s), 2)]))
        else:
            return bytes([int(s[x:x + 2], 16) for x in range(0, len(s), 2)])


class DIDResolver:
    @staticmethod
    def get_appdid_info(did: str):
        logging.info(f'get_appdid_info: did, {did}')
        if not did:
            raise BadRequestException(msg='get_appdid_info: did must provide.')

        c_did = lib.DID_FromString(did.encode())
        if not c_did:
            raise BadRequestException(msg=DIDResolver.get_errmsg("get_application_did_info: can't create c_did"))

        c_status = ffi.new("DIDStatus *")
        c_doc = lib.DID_Resolve(c_did, c_status, True)
        ffi.release(c_status)
        if not c_doc:
            msg = DIDResolver.get_errmsg("get_application_did_info: can't resolve c_doc")
            lib.DID_Destroy(c_did)
            raise BadRequestException(msg=msg)

        def get_appinfo_props(vc_json: dict):
            props = {'name': '', 'icon_url': '', 'redirect_url': ''}
            if 'credentialSubject' in vc_json:
                cs = vc_json['credentialSubject']
                props['name'] = cs.get('name', '')
                props['icon_url'] = cs.get('iconUrl', '')
                if 'endpoints' in vc_json:
                    props['icon_url'] = cs['endpoints'].get('redirectUrl', '')
            return props

        def get_developer_props(vc_json: dict):
            return {'developer_did': vc_json.get('issuer', '')}

        info = DIDResolver.get_info_from_credential(c_did, c_doc, 'appinfo', get_appinfo_props)
        info.update(DIDResolver.get_info_from_credential(c_did, c_doc, 'developer', get_developer_props))

        lib.DIDDocument_Destroy(c_doc)
        lib.DID_Destroy(c_did)
        return info

    @staticmethod
    def get_info_from_credential(c_did, c_doc, fragment: str, props_callback):
        c_did_url = lib.DIDURL_NewFromDid(c_did, fragment.encode())
        if not c_did_url:
            logging.error(DIDResolver.get_errmsg(f"get_application_did_info: can't create #{fragment} url"))
            return {}

        c_vc = lib.DIDDocument_GetCredential(c_doc, c_did_url)
        if not c_vc:
            msg = DIDResolver.get_errmsg(f"get_application_did_info: can't get #{fragment} credential")
            lib.DIDURL_Destroy(c_did_url)
            logging.error(msg)
            return {}

        if lib.Credential_IsValid(c_vc) != 1:
            msg = DIDResolver.get_errmsg(f"get_application_did_info: invalid #{fragment} credential")
            lib.DIDURL_Destroy(c_did_url)
            logging.error(msg)
            return {}

        c_vc_str = lib.Credential_ToJson(c_vc, True)
        if not c_vc_str:
            msg = DIDResolver.get_errmsg(f"get_application_did_info: can't get #{fragment} credential json")
            lib.DIDURL_Destroy(c_did_url)
            logging.error(msg)
            return {}

        return props_callback(json.loads(ffi.string(c_vc_str).decode()))

    @staticmethod
    def get_errmsg(prompt=None):
        """ helper method to get error message from did.so """
        error_msg, c_msg = 'unknown error', lib.DIDError_GetLastErrorMessage()
        if c_msg:
            error_msg = ffi.string(c_msg).decode()
        return error_msg if not prompt else f'{prompt}: {error_msg}'


if __name__ == '__main__':
    init_did_backend()
    info = DIDResolver.get_appdid_info('did:elastos:iqtWRVjz7gsYhyuQEb1hYNNmWQt1Z9geXg')
    print(f'appdid info: {info}')
