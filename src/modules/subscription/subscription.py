# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
from datetime import datetime

from hive.main.view import h_auth
from hive.util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_MAX_STORAGE, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE, VAULT_SERVICE_PRICING_USING
from hive.util.payment.payment_config import PaymentConfig
from src.utils.database_client import cli, VAULT_SERVICE_STATE_RUNNING
from src.utils.http_auth import check_auth
from src.utils.http_response import hive_restful_response, NotImplementedException, BadRequestException, ErrorCode


class VaultSubscription:
    def __init__(self):
        pass

    @hive_restful_response
    def subscribe(self, credential):
        if credential:
            raise NotImplementedException(msg='')
        return self._subscribe_free()

    def unsubscribe(self):
        pass

    def activate(self):
        pass

    def deactivate(self):
        pass

    def get_info(self):
        pass

    def _subscribe_free(self):
        did, app_id = check_auth()

        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did})
        if document:
            raise BadRequestException(code=ErrorCode.ALREADY_EXISTS, msg='The vault already exists.')

        price_plan = PaymentConfig.get_free_vault_info()
        document = self.__create_vault(did, price_plan)
        return {
            'pricingPlan': price_plan['name'],
            'serviceDid': h_auth.get_did_string(),
            'quota': price_plan["maxStorage"] * 1000 * 1000,
            'used': 0,
            'created': document[VAULT_SERVICE_START_TIME],
            'updated': document[VAULT_SERVICE_END_TIME],
        }

    def __create_vault(self, did, price_plan):
        now = datetime.utcnow().timestamp()
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_SERVICE_DID: did,
               VAULT_SERVICE_MAX_STORAGE: price_plan["maxStorage"],
               VAULT_SERVICE_FILE_USE_STORAGE: 0.0,
               VAULT_SERVICE_DB_USE_STORAGE: 0.0,
               VAULT_SERVICE_START_TIME: now,
               VAULT_SERVICE_END_TIME: end_time,
               VAULT_SERVICE_MODIFY_TIME: now,
               VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_SERVICE_PRICING_USING: price_plan['name']}
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {"$set": doc})
        return doc


class BackupSubscription:
    def __init__(self):
        pass

    def subscribe(self, credential):
        pass

    def unsubscribe(self):
        pass

    def activate(self):
        pass

    def deactivate(self):
        pass

    def get_info(self):
        pass
