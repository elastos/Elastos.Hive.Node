import json
from hive.util.did.ela_did_util import did_sign, init_test_did_store, did_verify

did_str = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym"
app_id = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym"
auth_key_name = "key2"
storepass = "123456"


def get_auth_token(self):
    rt, s = self.parse_response(
        self.test_client.post('/api/v1/did/auth',
                              data=json.dumps({
                                  "iss": did_str,
                                  "app_id": app_id
                              }),
                              headers=self.json_header)
    )
    self.assert200(s)
    self.assertEqual(rt["_status"], "OK")

    subject = rt["subject"]
    iss = rt["iss"]
    nonce = rt["nonce"]
    callback = rt["callback"]

    store, doc = init_test_did_store()
    sig = did_sign(did_str, doc, storepass, auth_key_name, nonce)
    param = dict()
    param["subject"] = subject
    param["realm"] = iss
    param["iss"] = did_str
    param["app_id"] = app_id
    param["nonce"] = nonce
    param["key_name"] = auth_key_name
    param["sig"] = str(sig, encoding="utf-8")

    r, s = self.parse_response(
        self.test_client.post(callback,
                              data=json.dumps(param),
                              headers=self.json_header)
    )
    self.assert200(s)
    self.assertEqual(r["_status"], "OK")
    return r["token"]
    print("token:" + r["token"])
