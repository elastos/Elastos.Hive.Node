# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
import json
import logging
import os
from datetime import datetime

from src import hive_setting
from src.utils_v1.constants import APP_INSTANCE_DID, DID_INFO_NONCE_EXPIRED
from src.utils.did.did_wrapper import Credential, DIDDocument, DID, JWT, Presentation
from src.utils.did.entity import Entity
from src.utils_v1.did_info import create_nonce, get_did_info_by_app_instance_did, add_did_nonce_to_db, \
    update_did_info_by_app_instance_did, get_did_info_by_nonce, update_token_of_did_info
from src.utils.http_client import HttpClient
from src.utils.http_exception import InvalidParameterException, BadRequestException

from src.utils.consts import URL_SIGN_IN, URL_BACKUP_AUTH, URL_V2
from src.utils.singleton import Singleton


class Auth(Entity, metaclass=Singleton):
    def __init__(self):
        Entity.__init__(self, "hive.auth", passphrase=hive_setting.PASSPHRASE, storepass=hive_setting.PASSWORD,
                        from_file=True, file_content=hive_setting.SERVICE_DID)
        self.http = HttpClient()
        logging.info(f'Service DID V2: {self.get_did_string()}')

    def sign_in(self, doc: dict):
        app_instance_did = self._get_app_instance_did(doc)
        return {
            "challenge": self._create_challenge(app_instance_did, *self._save_nonce_to_db(app_instance_did))
        }

    def _get_app_instance_did(self, app_instance_doc: dict) -> DID:
        doc_str = json.dumps(app_instance_doc)
        doc = DIDDocument.from_json(doc_str)
        if not doc.is_valid():
            raise BadRequestException(msg='The did document is invalid in getting app instance did.')
        did = doc.get_subject()

        # INFO: save application instance did document to /localdids folder
        spec_str = did.get_method_specific_id()
        try:
            with open(hive_setting.DID_DATA_LOCAL_DIDS + os.sep + spec_str, "w") as f:
                f.write(doc_str)
                f.flush()
        except Exception as e:
            raise BadRequestException(msg='Failed to cache application instance DID document.')

        return did

    def _save_nonce_to_db(self, app_instance_did):
        nonce, expire_time = create_nonce(), int(datetime.now().timestamp()) + hive_setting.AUTH_CHALLENGE_EXPIRED
        did_str = str(app_instance_did)
        try:
            if not get_did_info_by_app_instance_did(did_str):
                add_did_nonce_to_db(did_str, nonce, expire_time)
            else:
                update_did_info_by_app_instance_did(did_str, nonce, expire_time)
        except Exception as e:
            logging.getLogger("HiveAuth").error(f"Exception in __save_nonce_to_db: {e}")
            raise BadRequestException(msg='Failed to generate nonce.')
        return nonce, expire_time

    def _create_challenge(self, app_instance_did: DID, nonce: str, expire_time):
        """
        Create challenge for sign in response.
        """
        return super().create_jwt_token('DIDAuthChallenge', str(app_instance_did), expire_time, 'nonce', nonce, claim_json=False)

    def auth(self, challenge_response):
        credential_info = self._get_auth_info_from_challenge_response(challenge_response, ['appDid', ])
        access_token = self._create_access_token(credential_info, "AccessToken")

        try:
            update_token_of_did_info(credential_info["userDid"],
                                     credential_info["appDid"],
                                     credential_info["id"],
                                     credential_info["nonce"],
                                     access_token,
                                     credential_info["expTime"])
        except Exception as e:
            logging.error(f"Exception in __save_auth_info_to_db:: {e}")
            raise e

        return {
            "token": access_token,
        }

    def _get_auth_info_from_challenge_response(self, challenge_response, props=None):
        presentation_json, nonce, nonce_info = self._get_values_from_challenge_response(challenge_response)
        if nonce_info[DID_INFO_NONCE_EXPIRED] < int(datetime.now().timestamp()):
            raise BadRequestException(msg='The nonce expired.')
        credential_info = self._get_presentation_credential_info(presentation_json, props)
        if credential_info["id"] != nonce_info[APP_INSTANCE_DID]:
            raise BadRequestException(msg='The app instance did of the credential does not match.')
        credential_info["nonce"] = nonce
        return credential_info

    def _get_values_from_challenge_response(self, challenge_response):
        jwt: JWT = JWT.parse(challenge_response)
        vp_json = jwt.get_claim_as_json('presentation')
        vp: Presentation = Presentation.from_json(vp_json)
        if not vp.is_valid():
            raise BadRequestException(msg=f'The presentation is invalid')
        if vp.get_credential_count() < 1:
            raise BadRequestException(msg=f'No presentation credential exists')
        self._validate_presentation_realm(vp)
        nonce, nonce_info = self._get_presentation_nonce(vp)
        return json.loads(vp_json), nonce, nonce_info

    def _get_presentation_nonce(self, vp: Presentation):
        nonce = vp.get_nonce()
        nonce_info = get_did_info_by_nonce(nonce)
        if not nonce_info:
            raise BadRequestException(msg='Can not get presentation nonce information from database.')
        return nonce, nonce_info

    def _validate_presentation_realm(self, vp: Presentation):
        realm = vp.get_realm()
        if realm != super().get_did_string():
            raise BadRequestException(msg=f'Invalid presentation realm or not match.')

    def _get_presentation_credential_info(self, presentation_json, props=None):
        if "verifiableCredential" not in presentation_json:
            raise BadRequestException(msg='Verifiable credentials do not exist.')

        vcs_json = presentation_json["verifiableCredential"]
        if not isinstance(vcs_json, list):
            raise BadRequestException(msg="Verifiable credentials are not the list.")

        vc_json = vcs_json[0]
        if not vc_json:
            raise BadRequestException(msg='The credential is invalid.')
        if "credentialSubject" not in vc_json or type(vc_json["credentialSubject"]) != dict\
                or "issuer" not in vc_json:
            raise BadRequestException(msg='The credential subject is invalid or the issuer does not exist.')
        credential_info = vc_json["credentialSubject"]

        required_props = ['id', ]
        if props:
            required_props.extend(props)
        not_exist_props = list(filter(lambda p: p not in credential_info, required_props))
        if not_exist_props:
            raise BadRequestException(msg=f"The credentialSubject's prop ({not_exist_props}) does not exists.")

        credential_info["expTime"] = self._get_presentation_credential_expire_time(vcs_json)
        credential_info["userDid"] = vc_json["issuer"]
        return credential_info

    def _get_presentation_credential_expire_time(self, vcs_json):
        vc = Credential.from_json(json.dumps(vcs_json[0]))
        if not vc.is_valid():
            raise BadRequestException(msg='The presentation credential is invalid.')
        exp_time = vc.get_expiration_date()
        return min(int(datetime.now().timestamp()) + hive_setting.ACCESS_TOKEN_EXPIRED, exp_time)

    def _create_access_token(self, credential_info, subject) -> str:
        props = {k: credential_info[k] for k in credential_info if k not in ['id', 'expTime']}
        return super().create_jwt_token(subject, credential_info["id"], credential_info["expTime"], 'props', json.dumps(props), claim_json=False)

    def backup_auth(self, challenge_response):
        """ for the vault service node """
        credential_info = self._get_auth_info_from_challenge_response(challenge_response, ["targetHost", "targetDID"])
        access_token = self._create_access_token(credential_info, "BackupToken")
        return {'token': access_token}

    def get_backup_credential_info(self, credential):
        """ for vault /backup """
        credential_info, err = self._get_credential_info(credential, ["targetHost", "targetDID"])
        if credential_info is None:
            raise InvalidParameterException(msg=f'Failed to get credential info: {err}')
        return credential_info

    def backup_client_sign_in(self, host_url, credential: str, subject: str):
        """
        for vault /backup & /restore
        :return challenge_response, backup_service_instance_did
        """
        vc = Credential.from_json(credential)
        doc: dict = json.loads(self.get_doc().to_json())
        body = self.http.post(host_url + URL_V2 + URL_SIGN_IN, None, {"id": doc})
        if 'challenge' not in body or not body["challenge"]:
            raise InvalidParameterException(msg='backup_sign_in: failed to sign in to backup node.')

        jwt: JWT = JWT.parse(body["challenge"])
        audience = jwt.get_audience()
        if audience != self.get_did_string():
            raise InvalidParameterException(msg=f'backup_sign_in: failed to get the audience of the challenge.')

        nonce, issuer = jwt.get_claim('nonce'), jwt.get_issuer()
        vp_json = self.create_presentation_str(vc, nonce, issuer)
        challenge_response = self.create_vp_token(vp_json, subject, issuer, hive_setting.AUTH_CHALLENGE_EXPIRED)
        if challenge_response is None:
            raise InvalidParameterException(msg=f'backup_sign_in: failed to create the challenge response.')
        return challenge_response, issuer

    def backup_client_auth(self, host_url, challenge_response, backup_service_instance_did):
        """
        for vault /backup & /restore
        :return backup access token
        """
        body = self.http.post(host_url + URL_V2 + URL_BACKUP_AUTH, None, {"challenge_response": challenge_response})
        if 'token' not in body or not body["token"]:
            raise InvalidParameterException(msg='backup_auth: failed to backup auth to backup node.')

        jwt = JWT.parse(body["token"])
        audience = jwt.get_audience()
        if audience != self.get_did_string():
            raise InvalidParameterException(msg=f'backup_auth: failed to get the audience of the challenge.')

        issuer = jwt.get_issuer()
        if issuer != backup_service_instance_did:
            raise InvalidParameterException(msg=f'backup_auth: failed to get the issuer of the challenge.')

        return body["token"]

    def create_order_proof(self, user_did, doc_id, amount=0, is_receipt=False):
        exp = int(datetime.utcnow().timestamp()) + 7 * 24 * 3600 if not is_receipt else -1
        props = {'receipt_id': doc_id, 'amount': amount} if is_receipt else {'order_id': doc_id}
        return super().create_jwt_token('ORDER_PROOF', user_did, exp, 'props', json.dumps(props), claim_json=False)

    def verify_order_proof(self, proof, user_did, order_id):
        jwt = JWT.parse(proof)
        issuer = jwt.get_issuer()
        if issuer != super().get_did_string():
            raise BadRequestException(msg=f'the issue of the proof not match: {issuer}')

        audience = jwt.get_audience()
        if audience != user_did:
            raise BadRequestException(msg=f'the audience of the proof not match: {audience}')

        props = json.loads(jwt.get_claim('props'))
        if props.get('order_id') != order_id:
            raise BadRequestException(msg=f'the order_id of the proof not match: {props.get("order_id")}')

        expire, now = jwt.get_expiration(), int(datetime.now().timestamp())
        if now > expire:
            raise BadRequestException(msg=f'the proof is expired (valid for 7 days)')

    def get_ownership_presentation(self, credential: str):
        vc = Credential.from_json(credential)
        vp_json = self.create_presentation_str(vc, create_nonce(), super().get_did_string())
        return json.loads(vp_json)

    def _get_credential_info(self, vc_str, props: list):
        """
        :return: (dict, str)
        """
        vc: Credential = Credential.from_json(vc_str)
        if not vc.is_valid():
            return None, 'credential is invalid.'

        vc_json = json.loads(vc_str)
        if "credentialSubject" not in vc_json:
            return None, "The credentialSubject isn't exist."
        credential_subject = vc_json["credentialSubject"]

        if "id" not in credential_subject:
            return None, "The credentialSubject's id isn't exist."

        if 'sourceDID' not in props:
            props.append('sourceDID')

        for prop in props:
            if prop not in credential_subject:
                return None, "The credentialSubject's '" + prop + "' isn't exist."

        if credential_subject['sourceDID'] != super().get_did_string():
            return None, f'The sourceDID({credential_subject["sourceDID"]}) is not the hive node did.'

        if "issuer" not in vc_json:
            return None, "The credential issuer isn't exist."
        credential_subject["userDid"] = vc_json["issuer"]

        expire, exp = vc.get_expiration_date(), int(datetime.now().timestamp()) + hive_setting.ACCESS_TOKEN_EXPIRED
        if expire > exp:
            expire = exp

        credential_subject["expTime"] = expire
        return credential_subject, None


# INFO: create singleton object.
_auth = Auth()
