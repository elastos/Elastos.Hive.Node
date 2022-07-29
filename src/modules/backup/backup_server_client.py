import typing

from src.utils.consts import URL_V2, URL_SERVER_INTERNAL_STATE
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
            # action (None or 'backup'), state, message
            return body['state'], body['result'], body['message']
        except Exception as e:
            # backup service not exists
            raise BadRequestException(f'Failed to get the status from the backup server: {str(e)}')
