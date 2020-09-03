from datetime import datetime
from time import time

from hive.util.did_info import add_did_info_to_db, delete_did_info, get_did_info_by_token
from hive.util.did_sync import add_did_sync_info, update_did_sync_info, DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, \
    delete_did_sync_info

from hive.settings import AUTH_CHALLENGE_EXPIRE

did = "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM"
app_id = "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM"
nonce = "c4211de6-e297-11ea-9bab-acde48001122"
token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCJ9.eyJpc3MiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSIsICJzdWIiOiAiQWNjZXNzQXV0aG9yaXR5IiwgImV4cCI6IDE1OTc4OTYxMDQsICJhY2Nlc3NTdWJqZWN0IjogeyJpZCI6ICJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwgImFwcERpZCI6ICJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwgInB1cnBvc2UiOiAiZGlkOmVsYXN0b3M6aWVhQTVWTVd5ZFFtVkp0TTVkYVc1aG9UUXBjdVYzOG1ITSIsICJzY29wZSI6IFsicmVhZCIsICJ3cml0ZSJdLCAidXNlckRpZCI6ICJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIn19."
drive = "gdrive_ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM"


def setup_test_auth_token():
    delete_did_info(did, app_id)
    exp = int(datetime.now().timestamp()) + AUTH_CHALLENGE_EXPIRE
    add_did_info_to_db(did, app_id, nonce, token, exp)


def delete_test_auth_token():
    # delete_did_info(did, app_id)
    pass


def get_auth_token(self):
    return token


def setup_sync_record():
    delete_did_sync_info(did)
    add_did_sync_info(did, time(), drive)
    update_did_sync_info(did, DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, time(), drive)


def delete_sync_record():
    # delete_did_sync_info(did)
    pass
