import json
import logging

from src import init_did_backend
from src.utils.resolver import DIDResolver
from src.utils_v1.did.entity import Entity
from src.utils_v1.did.eladid import ffi, lib

logger = logging.getLogger()
logger.level = logging.DEBUG


class UserDID(Entity):
    issuer = None

    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase)
        self.issuer = lib.Issuer_Create(self.did, ffi.NULL, self.get_did_store())

    def __del__(self):
        lib.Issuer_Destroy(self.issuer)
        # Entity.__del__(self)

    def issue_auth(self, app):
        props = {
            'appDid': app.app_did,
        }
        return self.issue_auth_vc(self.issuer, "AppIdCredential", props, app.did)

    def issue_backup_auth(self, host_did, backup_url, backup_did):
        props = {
            'sourceDID': host_did,
            'targetHost': backup_url,
            'targetDID': backup_did,
        }
        did = lib.DID_FromString(host_did.encode())
        return self.issue_auth_vc(self.issuer, "BackupCredential", props, did)

    def get_owner_credential(self, owner_did):
        vc = self.issue_auth_vc(self.issuer, "HiveNodeOwnerCredential", {}, lib.DID_FromString(owner_did.encode()))
        vc_str = lib.Credential_ToString(vc, True)
        if not vc_str:
            print(f'get_owner_credential error: {DIDResolver.get_errmsg()}')
            return ''
        return ffi.string(vc_str).decode()


class AppDID(Entity):
    access_token = "123"
    app_did = "did:elastos:ienWaA6sfWETz6gVzX78SNytx8VUwDzxai"

    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase, need_resolve=False)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token


if __name__ == "__main__":
    import base58
    init_did_backend()
    # user did issue a new credential to service did.
    service_did = UserDID('hivenodeowner',
                          mnemonic='firm dash language credit twist puzzle crouch order slim now issue trap',
                          passphrase='secret')
    # service did
    credential = service_did.get_owner_credential('did:elastos:ipUGBPuAgEx6Le99f4TyDfNZtXVT2NKXPR')
    print(f'credential: {base58.b58encode(credential)}')
