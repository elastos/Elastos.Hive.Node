import json
import logging

from google_auth_oauthlib import flow

client_config = {"installed": {"client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com",
                               "project_id": "my-project-rclone-new",
                               "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                               "token_uri": "https://oauth2.googleapis.com/token",
                               "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                               "client_secret": "mqaI40MlghlNkfaFtDBzvpGg",
                               "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]}}


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.__str__()}


scopes = ['https://www.googleapis.com/auth/drive']  # example
appflow = flow.InstalledAppFlow.from_client_config(client_config, scopes=scopes)
appflow.run_console()
appflow.run_local_server()
credentials = appflow.credentials
c = credentials_to_dict(credentials)
logging.debug(json.dumps(c))
