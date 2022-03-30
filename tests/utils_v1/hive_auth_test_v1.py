import logging

from src import init_did_backend
from src.utils_v1.did.entity import Entity
from src.utils_v1.did.eladid import ffi, lib
from tests.utils_v1 import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG


class DIDApp(Entity):
    issuer = None

    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic, passphrase)
        self.issuer = lib.Issuer_Create(self.did, ffi.NULL, self.store)

    def __del__(self):
        lib.Issuer_Destroy(self.issuer)
        # Entity.__del__(self)

    def issue_auth(self, app):
        props = {
            'appDid': app.appId,
        }
        return self.issue_auth_vc("AppIdCredential", props, app.did)

    def issue_backup_auth(self, host_did, backup_url, backup_did):
        props = {
            'sourceDID': host_did,
            'targetHost': backup_url,
            'targetDID': backup_did,
        }
        did = lib.DID_FromString(host_did.encode())
        return self.issue_auth_vc("BackupCredential", props, did)

    def get_owner_credential(self, owner_did):
        vc = self.issue_auth_vc("HiveNodeOwnerCredential", {}, lib.DID_FromString(owner_did.encode()))
        vc_str = lib.Credential_ToString(vc, True)
        if not vc_str:
            print(f'get_owner_credential error: {self.get_error_message()}')
            return ''
        return ffi.string(vc_str).decode()

    def get_error_message(self, prompt=None):
        """ helper method to get error message from did.so """
        err_message = ffi.string(lib.DIDError_GetLastErrorMessage()).decode()
        return err_message if not prompt else f'[{prompt}] {err_message}'


class DApp(Entity):
    access_token = "123"
    appId = test_common.app_id

    def __init__(self, name, appId=None, mnemonic=None, passphrase=None):
        if (appId is not None):
            self.appId = appId
        Entity.__init__(self, name, mnemonic, passphrase, need_resolve=False)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token


if __name__ == "__main__":
    import base58
    init_did_backend()
    # owner did
    service_did = DIDApp('hivenode',
                         mnemonic='firm dash language credit twist puzzle crouch order slim now issue trap',
                         passphrase='secret')
    # user did
    credential = service_did.get_owner_credential('did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM')
    print(f'credential: {base58.b58encode(credential)}')
