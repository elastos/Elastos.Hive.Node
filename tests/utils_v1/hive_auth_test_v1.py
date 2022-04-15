import logging

from src.utils.did.did_wrapper import DID, Credential
from src.utils.did.entity import Entity

logger = logging.getLogger()
logger.level = logging.DEBUG


class UserDID(Entity):
    def __init__(self, name, mnemonic=None, passphrase=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase)

    def issue_auth(self, app: 'AppDID') -> Credential:
        props = {'appDid': AppDID.app_did}
        return super().create_credential('AppIdCredential', props, owner_did=app.did)

    def issue_backup_auth(self, host_did: str, backup_url, backup_did) -> Credential:
        props = {'sourceDID': host_did, 'targetHost': backup_url, 'targetDID': backup_did}
        return super().create_credential('BackupCredential', props, owner_did=DID.from_string(host_did))

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
