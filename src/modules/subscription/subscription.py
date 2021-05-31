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
from hive.util.payment.vault_service_manage import delete_user_vault_data
from src.modules.scripting.scripting import check_auth
from src.utils.database_client import cli, VAULT_SERVICE_STATE_RUNNING, VAULT_SERVICE_STATE_FREEZE
from src.utils.http_response import hive_restful_response, NotImplementedException, BadRequestException, ErrorCode, \
    hive_restful_code_response


class VaultSubscription:
    def __init__(self):
        pass

    @hive_restful_code_response
    def subscribe(self, credential):
        if credential:
            # TODO: Need support this with payment.
            raise NotImplementedException(msg='')
        return self._subscribe_free()

    def _subscribe_free(self):
        did, app_id = check_auth()
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did}, is_create=True)
        result = self.__get_vault_info(self.__create_vault(did, PaymentConfig.get_free_vault_info()))
        return result, 201 if not document else 200

    def __create_vault(self, did, price_plan):
        now = datetime.utcnow().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_SERVICE_DID: did,
               VAULT_SERVICE_MAX_STORAGE: price_plan["maxStorage"],
               VAULT_SERVICE_FILE_USE_STORAGE: 0.0,
               VAULT_SERVICE_DB_USE_STORAGE: 0.0,
               VAULT_SERVICE_START_TIME: now,
               VAULT_SERVICE_END_TIME: end_time,
               VAULT_SERVICE_MODIFY_TIME: now,
               VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_FREEZE,
               VAULT_SERVICE_PRICING_USING: price_plan['name']}
        col = cli.get_origin_collection(DID_INFO_DB_NAME, VAULT_SERVICE_COL, True)
        options = {
            "upsert": True,
            "bypass_document_validation": False
        }
        col.replace_one({VAULT_SERVICE_DID: did}, doc, **options)
        return doc

    def __get_vault_info(self, doc):
        return {
            'pricingPlan': doc[VAULT_SERVICE_PRICING_USING],
            'serviceDid': h_auth.get_did_string(),
            'storageQuota': doc[VAULT_SERVICE_MAX_STORAGE] * 1000 * 1000,
            'storageUsed': 0,
            'created': cli.timestamp_to_epoch(doc[VAULT_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_SERVICE_END_TIME]),
        }

    @hive_restful_response
    def unsubscribe(self):
        did, app_id = check_auth()
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did})
        if not document:
            raise BadRequestException(code=ErrorCode.VAULT_NOT_FOUND, msg='The vault does not exist.')
        delete_user_vault_data(did)
        cli.delete_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did})

    @hive_restful_response
    def activate(self):
        return self.update_vault_state(VAULT_SERVICE_STATE_RUNNING)

    def update_vault_state(self, status):
        did, app_id = check_auth()

        col_filter = {VAULT_SERVICE_DID: did}
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter)
        if not document:
            raise BadRequestException(code=ErrorCode.VAULT_NOT_FOUND, msg='The vault does not exist.')

        doc = {VAULT_SERVICE_DID: did,
               VAULT_SERVICE_MODIFY_TIME: datetime.utcnow().timestamp(),
               VAULT_SERVICE_STATE: status}
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter, {"$set": doc})

    @hive_restful_response
    def deactivate(self):
        self.update_vault_state(VAULT_SERVICE_STATE_FREEZE)

    @hive_restful_response
    def get_info(self):
        did, app_id = check_auth()

        col_filter = {VAULT_SERVICE_DID: did}
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter)
        if not document:
            raise BadRequestException(code=ErrorCode.VAULT_NOT_FOUND, msg='The vault does not exist.')

        return self.__get_vault_info(document)

    def get_price_plans(self, subscription, name):
        all_plans = PaymentConfig.get_all_package_info()
        result = {'version': all_plans.get('version', '1.0')}
        if subscription == 'all':
            result['backupPlans'] = self.__filter_plans_by_name(all_plans.get('backupPlans', []), name)
            result['pricingPlans'] = self.__filter_plans_by_name(all_plans.get('pricingPlans', []), name)
        elif subscription == 'vault':
            result['pricingPlans'] = self.__filter_plans_by_name(all_plans.get('pricingPlans', []), name)
        elif subscription == 'backup':
            result['backupPlans'] = self.__filter_plans_by_name(all_plans.get('backupPlans', []), name)
        return result

    def __filter_plans_by_name(self, plans, name):
        if not name:
            return plans

        return list(filter(lambda p: p.get('name') == name, plans))


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
