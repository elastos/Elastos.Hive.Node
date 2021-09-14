import logging

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
