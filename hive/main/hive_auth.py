import base58
from flask import request

from hive.main import view
from hive.util.did.ela_did_util import setup_did_backend, is_did_resolve, did_verify
from hive.util.did_info import add_did_info_to_db, create_token, save_token_to_db, create_nonce, \
    get_did_info_by_nonce, update_nonce_of_did_info, get_did_info_by_did_appid
from hive.util.server_response import response_err, response_ok

from hive.util.constants import DID_AUTH_REALM, DID_INFO_NONCE_EXPIRE, DID, APP_ID
from hive.settings import DID_CHALLENGE_EXPIRE, DID_TOKEN_EXPIRE
from datetime import datetime


class HiveAuth:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        setup_did_backend()

    def did_auth_challenge(self):
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        did = content.get('iss', None)
        app_id = content.get('app_id', None)
        if (did is None) or (app_id is None):
            return response_err(400, "parameter is null")

        ret = is_did_resolve(did)
        if not ret:
            return response_err(400, "parameter did error")

        nonce = create_nonce()
        time = datetime.now().timestamp()

        info = get_did_info_by_did_appid(did, app_id)

        try:
            if info is None:
                add_did_info_to_db(did, app_id, nonce, time + DID_CHALLENGE_EXPIRE)
            else:
                update_nonce_of_did_info(did, app_id, nonce, time + DID_CHALLENGE_EXPIRE)
        except Exception as e:
            print("Exception in did_auth_challenge::", e)
            return response_err(500, "Exception in did_auth_challenge:" + e)

        s_did = base58.b58encode(did)
        s_app_id = base58.b58encode(app_id)

        data = {
            "subject": "didauth",
            "iss": "elastos_hive_node",
            "nonce": nonce,
            "callback": "/api/v1/did/%s/%s/callback" % (str(s_did, encoding="utf-8"), str(s_app_id, encoding="utf-8"))
        }
        return response_ok(data)

    def did_auth_callback(self, did_base58, app_id_base58):
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        subject = content.get('subject', None)
        iss = content.get('iss', None)
        app_id_in = content.get('app_id', None)
        realm = content.get('realm', None)
        nonce = content.get('nonce', None)
        key_name = content.get('key_name', None)
        sig = content.get('sig', None)

        if (subject is None) \
                or (iss is None) \
                or (realm is None) \
                or (nonce is None) \
                or (key_name is None) \
                or (sig is None):
            return response_err(400, "parameter is null")

        # 0. 验证realm
        if realm != DID_AUTH_REALM:
            return response_err(406, "auth realm error")

        # 1. nonce找出数据库did, app_id 对比iss， url_did, app_id
        info = get_did_info_by_nonce(nonce)
        if info is None:
            return response_err(406, "auth nonce error")

        did = info[DID]
        app_id = info[APP_ID]
        url_did = base58.b58decode(did_base58)
        url_app_id = base58.b58decode(app_id_base58)
        if (did != str(url_did, encoding="utf-8")) or (app_id != str(url_app_id, encoding="utf-8")):
            return response_err(406, "auth url error")
        if did != iss:
            return response_err(406, "auth did error")
        if app_id != app_id_in:
            return response_err(406, "auth app_id error")

        # 2. 验证过期时间
        expire = info[DID_INFO_NONCE_EXPIRE]
        now = datetime.now().timestamp()
        if now > expire:
            return response_err(406, "auth expire error")

        # 3. 获取public key， 校验sig
        ret = did_verify(did, sig, key_name, nonce)
        if not ret:
            return response_err(406, "auth sig error")

        # 校验成功, 生成token
        token = create_token()
        save_token_to_db(did, app_id, token, now + DID_TOKEN_EXPIRE)

        # 设置eve
        view.hive_mongo.init_eve(did, app_id)

        data = {"token": token}
        return response_ok(data)
