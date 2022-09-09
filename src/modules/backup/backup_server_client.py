import typing

from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import URL_V2, URL_SERVER_INTERNAL_STATE, USR_DID, BACKUP_TARGET_TYPE, BACKUP_TARGET_TYPE_HIVE_NODE, COL_IPFS_BACKUP_CLIENT, \
    BACKUP_REQUEST_TARGET_HOST, BACKUP_REQUEST_TARGET_TOKEN
from src.utils.http_client import HttpClient
from src.utils.http_exception import BadRequestException
from src.modules.auth.auth import Auth


class BackupServerClient:
    def __init__(self, target_host: str, credential: typing.Optional[str] = None, token=None):
        self.target_host = target_host
        self.token = token
        self.credential = credential  # only for getting token
        self.auth = Auth()
        self.http = HttpClient()

    def get_token(self):
        if not self.token:
            try:
                challenge_response, backup_service_instance_did = \
                    self.auth.backup_client_sign_in(self.target_host, self.credential, 'DIDBackupAuthResponse')
                self.token = self.auth.backup_client_auth(self.target_host, challenge_response, backup_service_instance_did)
            except Exception as e:
                raise BadRequestException(f'Failed to get the token from the backup server: {str(e)}')

        return self.token

    def get_state(self):
        try:
            body = self.http.get(self.target_host + URL_V2 + URL_SERVER_INTERNAL_STATE, self.get_token())
            # action (None or 'backup'), state, message, public key for curve25519
            return body['state'], body['result'], body['message'], body['public_key']
        except Exception as e:
            # backup service not exists
            raise BadRequestException(f'Failed to get the status from the backup server: {str(e)}')

    @staticmethod
    def __get_request_doc(user_did):
        mcli = MongodbClient()
        filter_ = {USR_DID: user_did,
                   BACKUP_TARGET_TYPE: BACKUP_TARGET_TYPE_HIVE_NODE}
        return mcli.get_management_collection(COL_IPFS_BACKUP_CLIENT).find_one(filter_)

    @staticmethod
    def get_state_by_user_did(user_did):
        req = BackupServerClient.__get_request_doc(user_did)
        return BackupServerClient(req[BACKUP_REQUEST_TARGET_HOST], token=req[BACKUP_REQUEST_TARGET_TOKEN]).get_state()
