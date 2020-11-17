from datetime import datetime
from time import time

from hive.util.constants import DID_INFO_TOKEN
from hive.util.did_info import get_did_info_by_did_appid
from hive.util.did_sync import add_did_sync_info, update_did_sync_info, DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, \
    delete_did_sync_info

from hive.settings import AUTH_CHALLENGE_EXPIRED
from hive.util.payment.vault_service_manage import setup_vault_service

did = "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN"
app_id = "appid"
did2 = "did:elastos:ioLFi22fodmFUAFKia6uTV2W8Jz9vEcQyP"
app_id2 = "appid2"
# nonce = "c4211de6-e297-11ea-9bab-acde48001122"
token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZGZwS0pKMXNvRHhUMkdjZ0NSbkR0M2N1OTRabkdmek5YIiwiZXhwIjoxNjA4MTA4MDMyLCJ1c2VyRGlkIjoiZGlkOmVsYXN0b3M6aWo4a3JBVlJKaXRaS0ptY0N1Zm9MSFFqcTdNZWYzWmpUTiIsImFwcElkIjoiYXBwaWQiLCJhcHBJbnN0YW5jZURpZCI6ImRpZDplbGFzdG9zOmlkZnBLSkoxc29EeFQyR2NnQ1JuRHQzY3U5NFpuR2Z6TlgifQ.sLlmE9_Jwcn2ycO8jWM2R_J79DEbRv4TQUnjHRnuvv5TDKfkrFUB5ovjNN2pFjjLbvJf4BwGzVfPXXxct6esmA"
token2 = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZGZwS0pKMXNvRHhUMkdjZ0NSbkR0M2N1OTRabkdmek5YIiwiZXhwIjoxNjA1MjkwMzgxLCJ1c2VyRGlkIjoiZGlkOmVsYXN0b3M6aW9MRmkyMmZvZG1GVUFGS2lhNnVUVjJXOEp6OXZFY1F5UCIsImFwcElkIjoiYXBwaWQiLCJhcHBJbnN0YW5jZURpZCI6ImRpZDplbGFzdG9zOmlkZnBLSkoxc29EeFQyR2NnQ1JuRHQzY3U5NFpuR2Z6TlgifQ.RjNBt_D6Ax-JQbFU2kXHygdj50TDgoGWOew4oBO-P_N0SPDZbQhkIgESwHBweS5Fzsyx-zQVilp-Yxw6Fy2rqA"


def setup_test_auth_token():
    info = get_did_info_by_did_appid(did, app_id)
    if info:
        global token
        token = info[DID_INFO_TOKEN]

    info2 = get_did_info_by_did_appid(did, app_id)
    if info2:
        global token2
        token2 = info2[DID_INFO_TOKEN]
    return



def delete_test_auth_token():
    # delete_did_info(did, app_id)
    pass


def get_auth_did():
    return did


def get_auth_app_did():
    return app_id


def get_auth_token():
    return token


def get_auth_token2():
    return token2


def setup_test_vault(did):
    setup_vault_service(did, 100, -1)

